from fastapi import Request

from core.auth.auth_context import AuthContext


def set_audit_context(
    request: Request,
    *,
    event_key: str | None = None,
    auth_context: AuthContext | None = None,
    tipo: str | None = None,
    info: str | None = None,
) -> None:
    request.state.audit_context = {
        "event_key": event_key,
        "auth_context": auth_context,
        "tipo": tipo,
        "info": info,
    }

def resolve_audit_defaults(path: str, method: str) -> tuple[str, str]:
    segments = [segment for segment in path.strip("/").split("/") if segment]
    tipo = segments[2] if len(segments) >= 3 and segments[0] == "api" else (segments[0] if segments else "system")

    if tipo == "auth" and method == "POST" and path.endswith("/login"):
        return tipo, "Inicio de sesion"
    if tipo == "auth" and method == "POST" and path.endswith("/refresh"):
        return tipo, "Renovacion de sesion"
    if tipo == "auth" and method == "GET" and path.endswith("/me"):
        return tipo, "Consulta de usuario autenticado"
    if tipo == "users" and method == "POST":
        return tipo, "Creacion de usuario"
    if tipo == "users" and method == "DELETE":
        return tipo, "Eliminacion de usuario"
    if tipo == "users" and method == "GET":
        return tipo, "Consulta de usuarios"
    if tipo == "logs" and method == "GET":
        return tipo, "Consulta de logs"
    if tipo == "health" and method == "GET":
        return tipo, "Healthcheck"
    return tipo, f"{method} {path}"