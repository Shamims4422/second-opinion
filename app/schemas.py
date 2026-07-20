from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ToolName(StrEnum):
    browser = "browser"
    filesystem = "filesystem"
    shell = "shell"
    email = "email"


class ExperienceStatus(StrEnum):
    proposed = "proposed"
    approved = "approved"
    revised = "revised"
    blocked = "blocked"
    completed = "completed"


class ExperienceCreate(BaseModel):
    task: str = Field(min_length=1, max_length=2000)
    proposed_action: str = Field(min_length=1, max_length=2000)
    tool_name: ToolName
    environment_context: str | None = Field(default=None, max_length=4000)

    @field_validator("task", "proposed_action")
    @classmethod
    def must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty or whitespace")
        return stripped


class ExperienceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task: str
    proposed_action: str
    tool_name: ToolName
    environment_context: str | None
    status: ExperienceStatus
    created_at: datetime


class SimilarExperienceRead(BaseModel):
    experience_id: int
    task: str
    proposed_action: str
    tool_name: ToolName
    similarity: float
    was_successful: bool | None


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
