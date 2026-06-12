from __future__ import annotations

from datetime import date

from fastapi import Depends, Request, Response, status

from core.app.enums import UserRole
from core.app.state import AppState
from core.database.trazability_db import TrazabilityDB
from core.database.workspace_storage import workspace_relative_path
from core.errors.exceptions import AppError, NotFoundError
from core.utils.audit import set_audit_context
from src.dependencies.context import get_app_state, require_roles
from src.routers.base import APIRouter

router = APIRouter(prefix="/trazability", tags=["trazability"])


def _validate_db_date(db_date: str) -> str:
    try:
        date.fromisoformat(db_date)
    except ValueError as exc:
        raise AppError("db_date must use YYYY-MM-DD format") from exc
    return db_date


@router.post("/{db_date}/select", status_code=status.HTTP_204_NO_CONTENT)
def select_trazability_db(
    db_date: str,
    request: Request,
    _=Depends(require_roles(UserRole.ADMIN)),
    app_state: AppState = Depends(get_app_state),
) -> Response:
    validated_db_date = _validate_db_date(db_date)

    if (
        app_state.active_workspace_key is None
        or app_state.workspace_trazability_dbs is None
        or app_state.workspace_db is None
    ):
        raise AppError("An active workspace is required before selecting a trazability database")

    trazability_db_metadata = app_state.workspace_trazability_dbs.find_by_date(validated_db_date)
    if trazability_db_metadata is None:
        raise NotFoundError("Trazability database not found")

    trazability_db = TrazabilityDB(
        workspace_relative_path(
            app_state.settings,
            app_state.active_workspace_key,
            trazability_db_metadata["relative_path"],
        )
    )

    if not trazability_db.database_path.exists():
        raise NotFoundError("Trazability database file not found")

    app_state.active_trazability_db_date = validated_db_date
    app_state.active_trazability_db = trazability_db

    set_audit_context(
        request,
        tipo="trazability",
        info=f"Seleccion de base de trazabilidad: {validated_db_date}",
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
