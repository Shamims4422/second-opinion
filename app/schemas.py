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


class OutcomeSubmit(BaseModel):
    was_successful: bool
    outcome: str | None = Field(default=None, max_length=4000)
    failure_reason: str | None = Field(default=None, max_length=4000)


class OutcomeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    experience_id: int
    was_successful: bool
    outcome_description: str | None
    failure_reason: str | None
    recorded_at: datetime


class Decision(StrEnum):
    approve = "approve"
    revise = "revise"
    block = "block"


class SimilarEvidence(BaseModel):
    experience_id: int
    similarity: float
    was_successful: bool | None


class EvaluationRead(BaseModel):
    evaluation_id: int
    experience_id: int
    decision: Decision
    confidence: float
    reason: str
    evidence_count: int
    similar_experiences: list[SimilarEvidence]
    scoring_version: str


class EvaluationHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    experience_id: int
    confidence: float
    decision: Decision
    evidence_count: int
    scoring_version: str
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
