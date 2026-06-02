from __future__ import annotations

import re
import shutil
import sqlite3
import unicodedata
from pathlib import Path

from fastapi import Depends, Request, Response, status

from core.app.enums import UserRole
from core.app.state import AppState
from core.database.workspace_db import WorkspaceDB
from core.errors.exceptions import AppError, ConflictError, NotFoundError
from core.utils.audit import set_audit_context
from src.dependencies.context import get_app_state, require_roles
from src.routers.base import APIRouter
from src.schemas.workspace import WorkspaceCreate, WorkspaceRead, WorkspaceUpdate

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def _normalize_workspace_key(display_name: str) -> str:
    normalized_text = unicodedata.normalize("NFKD", display_name.strip())
    ascii_text = normalized_text.encode("ascii", "ignore").decode("ascii")
    workspace_key = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_text).strip("_").lower()
    workspace_key = re.sub(r"_+", "_", workspace_key)
    if not workspace_key:
        raise AppError("Workspace display_name is invalid")
    return workspace_key


def _workspace_db_path(app_state: AppState, workspace_key: str) -> Path:
    return app_state.settings.workspaces_dir / f"{workspace_key}.db"


def _activate_workspace(app_state: AppState, workspace_key: str) -> None:
    workspace_db = WorkspaceDB(_workspace_db_path(app_state, workspace_key))
    workspace_db.initialize()
    app_state.workspace_db = workspace_db
    app_state.active_workspace_key = workspace_key


def _rename_workspace_db(app_state: AppState, current_key: str, new_key: str) -> None:
    source_path = _workspace_db_path(app_state, current_key)
    target_path = _workspace_db_path(app_state, new_key)

    if source_path == target_path or not source_path.exists():
        return
    if target_path.exists():
        raise ConflictError("Workspace database file already exists")

    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source_path), str(target_path))


def _delete_workspace_db(app_state: AppState, workspace_key: str) -> None:
    workspace_db_path = _workspace_db_path(app_state, workspace_key)
    if workspace_db_path.exists():
        workspace_db_path.unlink()


def _raise_workspace_conflict(exc: sqlite3.IntegrityError) -> None:
    if "vision_workspace_dbs.workspace_key" in str(exc):
        raise ConflictError("Workspace key already exists") from exc
    raise ConflictError("Workspace conflict") from exc


@router.get("", response_model=list[WorkspaceRead])
def list_workspaces(
    request: Request,
    _=Depends(require_roles(UserRole.ADMIN)),
    app_state: AppState = Depends(get_app_state),
) -> list[WorkspaceRead]:
    set_audit_context(request, tipo="workspaces", info="Consulta de workspaces")
    workspaces = app_state.workspaces.list_all()
    return [WorkspaceRead.model_validate(item) for item in workspaces]


@router.post("", response_model=WorkspaceRead, status_code=status.HTTP_201_CREATED)
def create_workspace(
    request: Request,
    payload: WorkspaceCreate,
    _=Depends(require_roles(UserRole.ADMIN)),
    app_state: AppState = Depends(get_app_state),
) -> WorkspaceRead:
    workspace_key = _normalize_workspace_key(payload.display_name)
    try:
        workspace = app_state.workspaces.create(
            workspace_key=workspace_key,
            display_name=payload.display_name,
        )
    except sqlite3.IntegrityError as exc:
        _raise_workspace_conflict(exc)

    set_audit_context(
        request,
        tipo="workspaces",
        info=f"Creacion de workspace: {workspace_key}",
    )
    return WorkspaceRead.model_validate(workspace)


@router.post("/{workspace_key}/select", status_code=status.HTTP_204_NO_CONTENT)
def select_workspace(
    workspace_key: str,
    request: Request,
    _=Depends(require_roles(UserRole.ADMIN)),
    app_state: AppState = Depends(get_app_state),
) -> Response:
    workspace = app_state.workspaces.find_by_workspace_key(workspace_key)
    if workspace is None:
        raise NotFoundError("Workspace not found")

    _activate_workspace(app_state, workspace_key)
    set_audit_context(
        request,
        tipo="workspaces",
        info=f"Seleccion de workspace: {workspace_key}",
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{workspace_key}", response_model=WorkspaceRead)
def update_workspace(
    workspace_key: str,
    payload: WorkspaceUpdate,
    request: Request,
    _=Depends(require_roles(UserRole.ADMIN)),
    app_state: AppState = Depends(get_app_state),
) -> WorkspaceRead:
    current_workspace = app_state.workspaces.find_by_workspace_key(workspace_key)
    if current_workspace is None:
        raise NotFoundError("Workspace not found")

    new_workspace_key = _normalize_workspace_key(payload.display_name)
    try:
        updated_workspace = app_state.workspaces.update_by_workspace_key(
            workspace_key,
            new_workspace_key=new_workspace_key,
            display_name=payload.display_name,
        )
    except sqlite3.IntegrityError as exc:
        _raise_workspace_conflict(exc)

    if updated_workspace is None:
        raise NotFoundError("Workspace not found")

    try:
        _rename_workspace_db(app_state, workspace_key, new_workspace_key)
    except Exception:
        try:
            app_state.workspaces.update_by_workspace_key(
                new_workspace_key,
                new_workspace_key=workspace_key,
                display_name=current_workspace["display_name"],
            )
        except sqlite3.IntegrityError as exc:
            raise AppError("Workspace metadata rollback failed after database rename error") from exc
        raise

    if app_state.active_workspace_key == workspace_key:
        _activate_workspace(app_state, new_workspace_key)

    set_audit_context(
        request,
        tipo="workspaces",
        info=f"Actualizacion de workspace: {workspace_key}",
    )
    return WorkspaceRead.model_validate(updated_workspace)


@router.delete("/{workspace_key}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workspace(
    workspace_key: str,
    request: Request,
    _=Depends(require_roles(UserRole.ADMIN)),
    app_state: AppState = Depends(get_app_state),
) -> Response:
    workspace = app_state.workspaces.find_by_workspace_key(workspace_key)
    if workspace is None:
        raise NotFoundError("Workspace not found")

    deleted = app_state.workspaces.delete_by_workspace_key(workspace_key)
    if not deleted:
        raise NotFoundError("Workspace not found")

    _delete_workspace_db(app_state, workspace_key)
    if app_state.active_workspace_key == workspace_key:
        app_state.workspace_db = None
        app_state.active_workspace_key = None

    set_audit_context(
        request,
        tipo="workspaces",
        info=f"Eliminacion de workspace: {workspace_key}",
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
