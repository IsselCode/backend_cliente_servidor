from pydantic import BaseModel, Field


class PLCConfig(BaseModel):
    ip: str = Field(min_length=1)


class WorkspaceConfigPatch(BaseModel):
    config_plc: PLCConfig | None = None
    external_scanner: bool | None = None
    ok_piece: int | None = Field(default=None, ge=0)
    ng_piece: int | None = Field(default=None, ge=0)


class OutputWrite(BaseModel):
    value: bool
