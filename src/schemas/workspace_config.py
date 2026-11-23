from pydantic import BaseModel, Field

from src.schemas.plc import PLCStatus


class PLCConfig(BaseModel):
    ip: str = Field(min_length=1)


class WorkspaceConfigRead(BaseModel):
    config_plc: PLCConfig
    external_scanner: bool
    ok_piece: int
    ng_piece: int
    has_master_image: bool
    plc_status: PLCStatus


class WorkspaceConfigPatch(BaseModel):
    config_plc: PLCConfig | None = None
    external_scanner: bool | None = None
    ok_piece: int | None = Field(default=None, ge=0)
    ng_piece: int | None = Field(default=None, ge=0)
