from __future__ import annotations

from fastapi import Depends, Request, APIRouter

from core.app.enums import UserRole
from src.dependencies.context import require_roles, get_app_state
from src.schemas.business_settings import BusinessSettingsRead, BusinessSettingsUpdate

router = APIRouter(prefix="/settings/general", tags=["settings"])


@router.get("", response_model=BusinessSettingsRead)
def get_business_settings(
    request: Request,
    _=Depends(require_roles(UserRole.ADMIN, UserRole.SELLER, UserRole.DISPATCH)),
    app_state=Depends(get_app_state),
) -> BusinessSettingsRead:
    settings = app_state.business_settings.get()
    settings.pop("id", None)
    return BusinessSettingsRead.model_validate(settings)


@router.patch("", response_model=BusinessSettingsRead)
def update_business_settings(
    payload: BusinessSettingsUpdate,
    request: Request,
    _=Depends(require_roles(UserRole.ADMIN)),
    app_state=Depends(get_app_state),
) -> BusinessSettingsRead:
    updated = app_state.business_settings.update(**payload.model_dump(exclude_none=True))
    updated.pop("id", None)
    return BusinessSettingsRead.model_validate(updated)
