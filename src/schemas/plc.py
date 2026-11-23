from pydantic import BaseModel


class PLCStatus(BaseModel):
    workspace_key: str
    configured_ip: str
    connected_ip: str | None
    connected: bool


class OutputWrite(BaseModel):
    value: bool
