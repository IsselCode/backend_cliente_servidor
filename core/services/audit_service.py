from typing import Any

from core.database.repositories.audit_log_repository import AuditLogRepository
from core.database.repositories.business_settings_repository import BusinessSettingsRepository


class AuditService:
    def __init__(
        self,
        *,
        business_settings: BusinessSettingsRepository,
        audit_logs: AuditLogRepository,
    ) -> None:
        self.business_settings = business_settings
        self.audit_logs = audit_logs

    def is_enabled_for_client(self, event_key: str) -> bool:
        settings = self.business_settings.get()
        # Devuelve el valor de la llave si la llave se encuentra en el diccionario, si no, devuelve el "por defecto"
        return bool(settings.get(event_key, False))

    def record_event(
        self,
        *,
        event_key: str,
        user_uid: str | None,
        username: str | None,
        display_name: str | None,
        role: str | None,
        error_code: str | None = None,
        error_detail: str | None = None,
        error_meta: str | None = None,
        tipo: str,
        info: str,
        method: str,
        path: str,
        query_params: str | None,
        status_code: int,
        client_ip: str | None,
        duration_ms: float,
    ) -> bool:
        enabled = self.is_enabled_for_client(event_key)

        self.audit_logs.create(
            user_uid=user_uid,
            username=username,
            display_name=display_name,
            role=role,
            event_key=event_key,
            enabled=enabled,
            error_code=error_code,
            error_detail=error_detail,
            error_meta=error_meta,
            tipo=tipo,
            info=info,
            method=method,
            path=path,
            query_params=query_params,
            status_code=status_code,
            client_ip=client_ip,
            duration_ms=duration_ms,
        )
        return enabled

    def list_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.audit_logs.list_recent(limit)
