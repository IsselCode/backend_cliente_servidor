from __future__ import annotations

from datetime import date

from fastapi import Depends, Query, Request, APIRouter
from fastapi.exceptions import RequestValidationError

from core.app.enums import UserRole
from core.auth.auth_context import AuthContext
from core.utils.audit import set_audit_context
from src.dependencies.context import require_roles, get_app_state, get_current_auth_context
from src.schemas.log import AuditLogRead

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("", response_model=list[AuditLogRead])
def list_logs(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    _ = Depends(require_roles(UserRole.ADMIN)),
    app_state=Depends(get_app_state),
) -> list[AuditLogRead]:
    set_audit_context(
        request,
        tipo="logs",
        info="Consulta de logs"
    )
    return [AuditLogRead.model_validate(item) for item in app_state.audit_logs.list_recent(limit)]


@router.get("/range", response_model=list[AuditLogRead])
def list_logs_by_date_range(
    request: Request,
    start_date: date = Query(...),
    end_date: date = Query(...),
    limit: int = Query(default=200, ge=1, le=500),
    _ = Depends(require_roles(UserRole.ADMIN)),
    app_state=Depends(get_app_state),
) -> list[AuditLogRead]:
    if start_date > end_date:
        raise RequestValidationError(
            [
                {
                    "type": "value_error",
                    "loc": ("query", "start_date"),
                    "msg": "start_date must be less than or equal to end_date",
                }
            ]
        )

    set_audit_context(
        request,
        tipo="logs",
        info=f"Consulta de logs por rango: {start_date.isoformat()} - {end_date.isoformat()}",
    )

    return [
        AuditLogRead.model_validate(item)
        for item in app_state.audit_logs.list_by_date_range(start_date, end_date, limit)
    ]
