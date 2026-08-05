from fastapi import Depends, Request

from core.app.enums import UserRole
from core.app.state import AppState
from core.database.repositories.master_config_repository import MasterConfigRepository
from core.errors.exceptions import AuthorizationError, NotFoundError
from core.utils.audit import set_audit_context
from src.dependencies.context import get_app_state, require_roles
from src.routers.base import APIRouter
from src.schemas.plc import WorkspaceConfigPatch

router = APIRouter(prefix="/workspaces/{workspace_key}", tags=["workspace-config"])


def _repo(app_state: AppState, workspace_key: str) -> MasterConfigRepository:
    if app_state.workspaces.find_by_workspace_key(workspace_key) is None:
        raise NotFoundError("Workspace not found")
    if app_state.active_workspace_key != workspace_key or app_state.workspace_db is None:
        raise AuthorizationError("Workspace must be active")
    return MasterConfigRepository(app_state.workspace_db)


@router.get("/config")
def get_config(workspace_key: str, request: Request, _=Depends(require_roles(UserRole.ADMIN)), app_state: AppState = Depends(get_app_state)):
    repo = _repo(app_state, workspace_key)
    config = repo.get()
    config["plc_status"] = app_state.plc_service.status(workspace_key, config["config_plc"]["ip"])
    return config


@router.patch("/config")
def patch_config(workspace_key: str, payload: WorkspaceConfigPatch, request: Request, _=Depends(require_roles(UserRole.ADMIN)), app_state: AppState = Depends(get_app_state)):
    repo = _repo(app_state, workspace_key)
    old = repo.get()
    values = payload.model_dump(exclude_none=True)
    new_ip = values.get("config_plc", old["config_plc"])["ip"]
    old_ip = old["config_plc"]["ip"]
    updated = repo.update(**values)
    if new_ip != old_ip:
        app_state.plc_service.activate_workspace(workspace_key, new_ip)
    updated["plc_status"] = app_state.plc_service.status(workspace_key, new_ip)
    set_audit_context(request, tipo="workspace_config", info=f"Actualizacion de configuracion: {workspace_key}")
    return updated


@router.get("/counters")
def get_counters(workspace_key: str, _=Depends(require_roles(UserRole.ADMIN)), app_state: AppState = Depends(get_app_state)):
    config = _repo(app_state, workspace_key).get()
    return {"ok_piece": config["ok_piece"], "ng_piece": config["ng_piece"]}


@router.post("/counters/reset")
def reset_counters(workspace_key: str, _=Depends(require_roles(UserRole.ADMIN)), app_state: AppState = Depends(get_app_state)):
    config = _repo(app_state, workspace_key).reset_counters()
    return {"ok_piece": config["ok_piece"], "ng_piece": config["ng_piece"]}
