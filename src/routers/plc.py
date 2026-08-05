from fastapi import Depends, Request

from core.app.enums import UserRole
from core.app.state import AppState
from core.database.repositories.master_config_repository import MasterConfigRepository
from core.errors.exceptions import AuthorizationError, NotFoundError
from src.dependencies.context import get_app_state, require_roles
from src.routers.base import APIRouter
from src.schemas.plc import OutputWrite

router = APIRouter(prefix="/workspaces/{workspace_key}/plc", tags=["plc"])


def _config(app_state: AppState, workspace_key: str):
    if app_state.workspaces.find_by_workspace_key(workspace_key) is None:
        raise NotFoundError("Workspace not found")
    if app_state.active_workspace_key != workspace_key or app_state.workspace_db is None:
        raise AuthorizationError("Workspace must be active")
    return MasterConfigRepository(app_state.workspace_db).get()


@router.get("/status")
def status(workspace_key: str, _=Depends(require_roles(UserRole.ADMIN)), app_state: AppState = Depends(get_app_state)):
    config = _config(app_state, workspace_key)
    return app_state.plc_service.status(workspace_key, config["config_plc"]["ip"])


@router.post("/outputs/{output_name}")
def output(workspace_key: str, output_name: str, payload: OutputWrite, request: Request, _=Depends(require_roles(UserRole.ADMIN)), app_state: AppState = Depends(get_app_state)):
    _config(app_state, workspace_key)
    if output_name not in {"q1", "q2", "q3", "q4"}:
        raise NotFoundError("Output not found")
    success = app_state.plc_service.write_output(output_name, payload.value)
    return {"output_name": output_name, "value": payload.value, "success": success}
