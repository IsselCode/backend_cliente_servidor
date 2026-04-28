from pydantic import BaseModel, ConfigDict, Field


class BusinessSettingsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_created: bool
    user_deleted: bool
    user_modified: bool
    login: bool
    logout: bool


class BusinessSettingsUpdate(BaseModel):
    user_created: bool | None = None
    user_deleted: bool | None = None
    user_modified: bool | None = None
    login: bool | None = None
    logout: bool | None = None
