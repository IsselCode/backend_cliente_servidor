from pydantic import BaseModel, ConfigDict


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_uid: str | None
    username: str | None
    display_name: str | None
    role: str | None
    event_key: str | None
    enabled: bool
    error_code: str | None
    error_detail: str | None
    error_meta: str | None
    tipo: str
    info: str
    method: str
    path: str
    query_params: str | None
    status_code: int
    client_ip: str | None
    duration_ms: float
    created_at: str
