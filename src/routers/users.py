from __future__ import annotations

from fastapi import Depends, Query, Request, Response, status, APIRouter

from core.app.enums import UserRole
from core.app.state import AppState
from core.auth.auth_context import AuthContext
from core.errors.exceptions import ConflictError, NotFoundError
from src.dependencies.context import get_app_state, require_roles
from src.schemas.user import UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRead])
def list_users(
    name: str | None = Query(default=None, min_length=1, max_length=100),
    _=Depends(require_roles(UserRole.ADMIN)),
    app_state: AppState =Depends(get_app_state),
) -> list[UserRead]:
    if name:
        users = app_state.users.search_by_name(name)
    else:
        users = app_state.users.list_all()
    return [UserRead.model_validate(item) for item in users]


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    _=Depends(require_roles(UserRole.ADMIN)),
    app_state: AppState = Depends(get_app_state),
) -> UserRead:
    existing_user = app_state.users.find_by_username(payload.username)
    if existing_user:
        raise ConflictError("Username already exists")

    user = app_state.users.create_user(
        username=payload.username,
        dp_name=payload.display_name,
        password_hash=app_state.password_service.hash_password(payload.password),
        role=payload.role,
    )

    return UserRead.model_validate(user)


@router.patch("/{uid}", response_model=UserRead)
def update_user(
    uid: str,
    payload: UserUpdate,
    current_user: AuthContext = Depends(require_roles(UserRole.ADMIN)),
    app_state: AppState =Depends(get_app_state),
) -> UserRead:
    existing_user = app_state.users.find_by_uid(uid)
    if not existing_user:
        raise NotFoundError("User not found")

    if payload.username and payload.username != existing_user["username"]:
        user_with_same_username = app_state.users.find_by_username(payload.username)
        if user_with_same_username:
            raise ConflictError("Username already exists")

    if payload.is_active is False and current_user.uid == uid:
        raise ConflictError("Admin cannot deactivate the current authenticated user")

    updated_user = app_state.users.update_by_uid(
        uid,
        username=payload.username,
        display_name=payload.display_name,
        password_hash=(
            app_state.password_service.hash_password(payload.password)
            if payload.password is not None
            else None
        ),
        role=payload.role,
        is_active=payload.is_active,
    )

    return UserRead.model_validate(updated_user)


@router.delete("/{uid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    uid: str,
    request: Request,
    current_user: AuthContext = Depends(require_roles(UserRole.ADMIN)),
    app_state: AppState =Depends(get_app_state),
) -> Response:
    if current_user.uid == uid:
        raise ConflictError("Admin cannot delete the current authenticated user")

    deleted = app_state.users.delete_by_uid(uid)
    if not deleted:
        raise NotFoundError("User not found")

    return Response(status_code=status.HTTP_204_NO_CONTENT)
