from pydantic import BaseModel, ConfigDict, Field, field_validator


class WorkspaceCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=100)

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError("display_name must not be empty")

        if not all(char.isalnum() or char.isspace() for char in normalized_value):
            raise ValueError("display_name must contain only letters, numbers, and spaces")

        return normalized_value


class WorkspaceUpdate(BaseModel):
    display_name: str = Field(min_length=1, max_length=100)

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError("display_name must not be empty")

        if not all(char.isalnum() or char.isspace() for char in normalized_value):
            raise ValueError("display_name must contain only letters, numbers, and spaces")

        return normalized_value


class WorkspaceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    workspace_key: str
    display_name: str
    created_at: str
