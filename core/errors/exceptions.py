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
