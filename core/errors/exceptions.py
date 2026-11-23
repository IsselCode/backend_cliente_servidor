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


class MasterImageError(AppError):
    status_code = 503
    code = "master_image_error"
    detail = "No se pudo capturar la imagen maestra"


class MasterImageLightingError(MasterImageError):
    code = "master_image_lighting_error"
    detail = "No se pudo controlar la iluminacion de Q1"


class MasterImageTimeoutError(MasterImageError):
    status_code = 504
    code = "master_image_timeout"
    detail = "No llego una imagen nueva dentro del plazo de captura"


class MasterImageEncodingError(MasterImageError):
    status_code = 500
    code = "master_image_encoding_error"
    detail = "No se pudo codificar la imagen maestra como PNG"
