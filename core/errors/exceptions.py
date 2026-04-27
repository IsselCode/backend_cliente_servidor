class AppError(Exception):
    status_code = 400
    code = "application_error"
    detail = "Application error"

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.detail
        super().__init__(self.detail)

class AuthenticationError(AppError):
    status_code = 401
    code = "authentication_error"
    detail = "Authentication error"

class AuthorizationError(AppError):
    status_code = 403
    code = "authorization_error"
    detail = "Insufficient permissions"


class ConflictError(AppError):
    status_code = 409
    code = "conflict_error"
    detail = "Resource conflict"


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"
    detail = "Resource not found"
