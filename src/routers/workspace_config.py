from fastapi import Depends, Request, Response

from core.app.enums import UserRole
from core.app.state import AppState
from core.database.repositories.master_config_repository import MasterConfigRepository
from core.errors.exceptions import AuthorizationError, NotFoundError
from core.utils.audit import set_audit_context
from src.dependencies.context import get_app_state, require_roles
from src.routers.base import APIRouter
from src.schemas.workspace_config import WorkspaceConfigPatch, WorkspaceConfigRead

router = APIRouter(prefix="/workspaces/{workspace_key}", tags=["workspace-config"])

_PNG_CONTENT = {"image/png": {"schema": {"type": "string", "format": "binary"}}}
_PNG_HEADERS = {"Cache-Control": "no-store"}


def _repo(app_state: AppState, workspace_key: str) -> MasterConfigRepository:
    if app_state.workspaces.find_by_workspace_key(workspace_key) is None:
        raise NotFoundError("Workspace not found")
    if app_state.active_workspace_key != workspace_key or app_state.workspace_db is None:
        raise AuthorizationError("Workspace must be active")
    return MasterConfigRepository(app_state.workspace_db)


def _config_response(config: dict, app_state: AppState, workspace_key: str) -> dict:
    config["has_master_image"] = config.pop("master_img") is not None
    config["plc_status"] = app_state.plc_service.status(workspace_key, config["config_plc"]["ip"])
    return config


@router.get("/config", response_model=WorkspaceConfigRead)
def get_config(workspace_key: str, request: Request, _=Depends(require_roles(UserRole.ADMIN)), app_state: AppState = Depends(get_app_state)):
    repo = _repo(app_state, workspace_key)
    config = repo.get()
    return _config_response(config, app_state, workspace_key)


@router.patch("/config", response_model=WorkspaceConfigRead)
def patch_config(workspace_key: str, payload: WorkspaceConfigPatch, request: Request, _=Depends(require_roles(UserRole.ADMIN)), app_state: AppState = Depends(get_app_state)):
    repo = _repo(app_state, workspace_key)
    old = repo.get()
    values = payload.model_dump(exclude_none=True)
    new_ip = values.get("config_plc", old["config_plc"])["ip"]
    old_ip = old["config_plc"]["ip"]
    updated = repo.update(**values)
    if new_ip != old_ip:
        app_state.plc_service.activate_workspace(workspace_key, new_ip)
    set_audit_context(request, tipo="workspace_config", info=f"Actualizacion de configuracion: {workspace_key}")
    return _config_response(updated, app_state, workspace_key)


@router.post(
    "/master-image/capture", response_class=Response,
    summary="Capturar y guardar la imagen maestra",
    responses={
        200: {
            "description": "PNG capturado y guardado automaticamente como maestra",
            "content": _PNG_CONTENT,
            "headers": {
                "X-Frame-Id": {"schema": {"type": "string"}},
                "X-Captured-At": {"schema": {"type": "string", "format": "date-time"}},
                "X-Image-Width": {"schema": {"type": "integer"}},
                "X-Image-Height": {"schema": {"type": "integer"}},
            },
        },
        401: {"description": "Autenticacion requerida"},
        403: {"description": "Rol no autorizado o workspace inactivo"},
        404: {"description": "Workspace inexistente"},
        409: {"description": "Captura maestra en curso"},
        500: {"description": "Fallo de codificacion o persistencia"},
        503: {"description": "PLC, iluminacion o camara no disponibles"},
        504: {"description": "Plazo de captura agotado"},
    },
)
def capture_master_image(
    workspace_key: str, request: Request,
    _=Depends(require_roles(UserRole.ADMIN)),
    app_state: AppState = Depends(get_app_state),
) -> Response:
    repo = _repo(app_state, workspace_key)
    config = repo.get()
    set_audit_context(request, tipo="master_image", info=f"Captura de imagen maestra: {workspace_key}")
    captured = app_state.master_image_service.capture_and_save(
        repo, workspace_key=workspace_key, configured_ip=config["config_plc"]["ip"],
    )
    return Response(
        content=captured.png, media_type="image/png",
        headers=_PNG_HEADERS | {
            "X-Frame-Id": captured.frame.frame_id,
            "X-Captured-At": captured.frame.captured_at.isoformat().replace("+00:00", "Z"),
            "X-Image-Width": str(captured.frame.width),
            "X-Image-Height": str(captured.frame.height),
        },
    )


@router.get(
    "/master-image", response_class=Response,
    summary="Consultar la imagen maestra guardada",
    responses={
        200: {"description": "Imagen maestra almacenada como PNG", "content": _PNG_CONTENT},
        401: {"description": "Autenticacion requerida"},
        403: {"description": "Rol no autorizado o workspace inactivo"},
        404: {"description": "Workspace o imagen maestra inexistentes"},
    },
)
def get_master_image(
    workspace_key: str, request: Request,
    _=Depends(require_roles(UserRole.ADMIN)),
    app_state: AppState = Depends(get_app_state),
) -> Response:
    image_bytes = _repo(app_state, workspace_key).get_master_image()
    if image_bytes is None:
        raise NotFoundError("No hay una imagen maestra guardada en este workspace")
    set_audit_context(request, tipo="master_image", info=f"Consulta de imagen maestra: {workspace_key}")
    return Response(content=image_bytes, media_type="image/png", headers=_PNG_HEADERS)


@router.get("/counters")
def get_counters(workspace_key: str, _=Depends(require_roles(UserRole.ADMIN)), app_state: AppState = Depends(get_app_state)):
    config = _repo(app_state, workspace_key).get()
    return {"ok_piece": config["ok_piece"], "ng_piece": config["ng_piece"]}


@router.post("/counters/reset")
def reset_counters(workspace_key: str, _=Depends(require_roles(UserRole.ADMIN)), app_state: AppState = Depends(get_app_state)):
    config = _repo(app_state, workspace_key).reset_counters()
    return {"ok_piece": config["ok_piece"], "ng_piece": config["ng_piece"]}
