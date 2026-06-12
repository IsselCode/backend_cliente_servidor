from __future__ import annotations

import re
import sqlite3
import unicodedata

from fastapi import Depends, Request, Response, status

from core.app.enums import UserRole
from core.app.state import AppState
from core.database.repositories.workspace_trazability_db_repository import WorkspaceTrazabilityDBRepository
from core.database.workspace_storage import delete_workspace_storage, initialize_workspace_db
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


def _activate_workspace(app_state: AppState, workspace_key: str) -> None:
    workspace_db = initialize_workspace_db(app_state.settings, workspace_key)
    app_state.workspace_db = workspace_db
    app_state.workspace_trazability_dbs = WorkspaceTrazabilityDBRepository(workspace_db)
    app_state.active_workspace_key = workspace_key
    app_state.active_trazability_db_date = None
    app_state.active_trazability_db = None


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

    initialize_workspace_db(app_state.settings, workspace_key)
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
    try:
        updated_workspace = app_state.workspaces.update_by_workspace_key(
            workspace_key,
            display_name=payload.display_name,
        )
    except sqlite3.IntegrityError as exc:
        _raise_workspace_conflict(exc)

    if updated_workspace is None:
        raise NotFoundError("Workspace not found")

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

    delete_workspace_storage(app_state.settings, workspace_key)
    if app_state.active_workspace_key == workspace_key:
        app_state.workspace_db = None
        app_state.workspace_trazability_dbs = None
        app_state.active_workspace_key = None
        app_state.active_trazability_db_date = None
        app_state.active_trazability_db = None

    set_audit_context(
        request,
        tipo="workspaces",
        info=f"Eliminacion de workspace: {workspace_key}",
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
