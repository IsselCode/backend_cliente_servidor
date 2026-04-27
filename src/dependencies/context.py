from fastapi.requests import Request
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from core.app.enums import UserRole
from core.app.state import AppState
from core.auth.auth_context import AuthContext
from core.errors.exceptions import AuthenticationError, AuthorizationError

bearer_scheme = HTTPBearer(auto_error=False)

def get_app_state(request: Request) -> AppState:
    return request.app.state.container

def get_current_auth_context(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    app_state: AppState = Depends(get_app_state),
) -> AuthContext:
    if credentials is None:
        raise AuthenticationError("Authorization header is required")

    if credentials.scheme.lower() != "bearer":
        raise AuthenticationError("Authorization scheme is invalid")

    payload = app_state.token_manager.decode_access_token(credentials.credentials)
    user = app_state.users.find_by_uid(payload["uid"])
    if not user or not user["is_active"]:
        raise AuthenticationError("User is inactive or does not exist")

    auth_context = AuthContext.from_payload(payload)
    request.state.auth_context = auth_context
    return auth_context

def require_roles(*allowed_roles: UserRole):
    allowed_values = {role.value for role in allowed_roles}

    def dependency(auth_context: AuthContext = Depends(get_current_auth_context)) -> AuthContext:
        if auth_context.role not in allowed_values:
            raise AuthorizationError("User role is not allowed for this operation")
        return auth_context

    return dependency