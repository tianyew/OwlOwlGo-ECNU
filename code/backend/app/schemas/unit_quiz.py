"""Only learner choices, a content version and a retry key may be submitted."""

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UnitAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question_id: str = Field(min_length=1, max_length=80)
    selected_index: Annotated[int, Field(strict=True, ge=0, le=3)]


class SubmitUnitQuiz(BaseModel):
    model_config = ConfigDict(extra="forbid")
    submission_id: UUID
    content_version: int = Field(strict=True, ge=1)
    revision: int = Field(strict=True, ge=0)
    answers: list[UnitAnswer] = Field(min_length=1, max_length=10)


class ResetAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(strict=True, ge=0)
