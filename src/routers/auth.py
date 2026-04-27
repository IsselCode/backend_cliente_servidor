from fastapi import APIRouter, Depends

from core.app.state import AppState
from core.auth.auth_context import AuthContext
from core.errors.exceptions import AuthenticationError
from src.dependencies.context import get_app_state, get_current_auth_context
from src.schemas.auth import TokenResponse, LoginRequest, RefreshTokenRequest
from src.schemas.user import UserRead

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, app_state: AppState = Depends(get_app_state)) -> TokenResponse:
    user = app_state.users.find_by_username(payload.username)
    if not user or not user["is_active"]:
        raise AuthenticationError("Invalid username or password")

    is_valid_password = app_state.password_service.verify_password(
        payload.password,
        user["password_hash"],
    )
    if not is_valid_password:
        raise AuthenticationError("Invalid username or password")

    access_token = app_state.token_manager.create_access_token(
        uid=user["uid"],
        username=user["username"],
        dp=user["display_name"],
        role=user["role"],
    )
    refresh_token, jti, expires_at = app_state.token_manager.create_refresh_token(uid=user["uid"])
    app_state.refresh_tokens.create(jti=jti, user_uid=user["uid"], token=refresh_token, expires_at=expires_at)

    return TokenResponse(
        uid=user["uid"],
        username=user["username"],
        display_name=user["display_name"],
        role=user["role"],
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=app_state.settings.jwt_expiration_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_session(payload: RefreshTokenRequest, app_state: AppState=Depends(get_app_state)) -> TokenResponse:
    token_payload = app_state.token_manager.decode_refresh_token(payload.refresh_token)
    stored_token = app_state.refresh_tokens.find_active_by_token(payload.refresh_token)
    if not stored_token or stored_token["jti"] != token_payload["jti"] or stored_token["user_uid"] != token_payload["uid"]:
        raise AuthenticationError("Refresh token is invalid")

    user = app_state.users.find_by_uid(token_payload["uid"])
    if not user or not user["is_active"]:
        raise AuthenticationError("User is inactive or does not exist")

    app_state.refresh_tokens.revoke_by_jti(stored_token["jti"])

    access_token = app_state.token_manager.create_access_token(
        uid=user["uid"],
        username=user["username"],
        dp=user["display_name"],
        role=user["role"],
    )
    refresh_token, new_jti, expires_at = app_state.token_manager.create_refresh_token(uid=user["uid"])
    app_state.refresh_tokens.create(jti=new_jti, user_uid=user["uid"], token=refresh_token, expires_at=expires_at)

    return TokenResponse(
        uid=user["uid"],
        username=user["username"],
        display_name=user["display_name"],
        role=user["role"],
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=app_state.settings.jwt_expiration_minutes * 60,
    )


@router.get("/me", response_model=UserRead)
def me(auth_context: AuthContext = Depends(get_current_auth_context), app_state:AppState=Depends(get_app_state),) -> UserRead:
    user = app_state.users.find_by_uid(auth_context.uid)
    return UserRead.model_validate(user)

