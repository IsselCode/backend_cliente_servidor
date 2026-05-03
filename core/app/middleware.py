import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from core.app.state import AppState
from core.auth.auth_context import AuthContext
from core.utils.audit import resolve_audit_defaults


class AuditLogMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        started_at = time.perf_counter()
        status_code = 500
        response: Response | None = None

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            app_state: AppState = request.app.state.container
            elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
            audit_context = getattr(request.state, "audit_context", None) or {}
            auth_context: AuthContext = (audit_context.get("auth_context") or getattr(request.state, "auth_context", None))
            default_tipo, default_info = resolve_audit_defaults(request.url.path, request.method)

            payload = {
                "user_uid": auth_context.uid if auth_context else None,
                "username": auth_context.username if auth_context else None,
                "display_name": auth_context.display_name if auth_context else None,
                "role": auth_context.role if auth_context else None,
                "tipo": audit_context.get("tipo") or default_tipo,
                "info": audit_context.get("info") or default_info,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params) if request.query_params else None,
                "status_code": status_code,
                "client_ip": request.client.host if request.client else None,
                "duration_ms": elapsed_ms,
            }

            audit_error = getattr(request.state, "audit_error", None) or {}
            payload["error_code"] = audit_error.get("error_code")
            payload["error_detail"] = audit_error.get("error_detail")
            payload["error_meta"] = audit_error.get("error_meta")

            event_key = audit_context.get("event_key")
            if event_key:
                app_state.audit_service.record_event(event_key=event_key, **payload)
            else:
                app_state.audit_logs.create(**payload)





