"""Explainable learner-profile contract for language ability and cognition.

This module is intentionally independent from the current demo progress document.
It defines the next profile version without changing already saved user records.
"""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

BloomLevel = Literal["remember", "understand", "apply", "analyze", "evaluate", "create"]
LanguageDimension = Literal[
    "phonetics",
    "vocabulary_grammar",
    "functional_reading",
    "multimodal_information_literacy",
    "poetry_comprehension",
    "classical_chinese_comprehension",
    "written_language_use",
]
EvidenceStatus = Literal["insufficient", "emerging", "stable"]

HINT_WEIGHTS = {0: 1.0, 1: 0.85, 2: 0.70, 3: 0.50, 4: 0.20}


class ProfileEvidence(BaseModel):
    """One auditable task attempt used to update exactly one profile cell."""

    model_config = ConfigDict(extra="forbid")
    attempt_id: str = Field(min_length=1)
    item_id: str = Field(min_length=1)
    language_dimension: LanguageDimension
    bloom_level: BloomLevel
    correct: bool
    hint_level: int = Field(ge=0, le=4)
    response_time_ms: int | None = Field(default=None, ge=0)
    attempt_count: int = Field(default=1, ge=1)
    difficulty_weight: float = Field(default=1.0, ge=0.8, le=1.2)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def performance(self) -> float:
        """Coursework heuristic, not a psychometrically validated ability estimate."""
        if not self.correct:
            return 0.0
        retry_weight = max(0.7, 1.0 - 0.1 * (self.attempt_count - 1))
        return round(
            min(1.0, HINT_WEIGHTS[self.hint_level] * retry_weight * self.difficulty_weight),
            4,
        )


class ProfileCell(BaseModel):
    """A cell in the LanguageDimension x BloomLevel matrix."""

    model_config = ConfigDict(extra="forbid")
    score: float | None = Field(default=None, ge=0, le=1)
    confidence: float = Field(default=0, ge=0, le=1)
    evidence_count: int = Field(default=0, ge=0)
    status: EvidenceStatus = "insufficient"
    last_updated_at: datetime | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class LearnerProfileSnapshot(BaseModel):
    """Versioned, explainable snapshot used by planning and scaffolding."""

    model_config = ConfigDict(extra="forbid")
    learner_id: str = Field(min_length=1)
    profile_version: int = Field(default=1, ge=1)
    scoring_policy_version: Literal["profile-heuristic-v1"] = "profile-heuristic-v1"
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    matrix: dict[LanguageDimension, dict[BloomLevel, ProfileCell]] = Field(default_factory=dict)
    interests: list[Literal["travel", "daily", "campus", "poetry"]] = Field(
        default_factory=list
    )
    preferred_scaffold_level: int = Field(default=1, ge=0, le=4)


def update_cell(previous: ProfileCell, evidence: ProfileEvidence) -> ProfileCell:
    """Update a cell while retaining an auditable bounded evidence window."""
    observation = evidence.performance()
    score = observation if previous.score is None else previous.score * 0.7 + observation * 0.3
    count = previous.evidence_count + 1
    status: EvidenceStatus = "stable" if count >= 5 else "emerging" if count >= 2 else "insufficient"
    return ProfileCell(
        score=round(score, 4),
        confidence=round(min(1.0, count / 5), 2),
        evidence_count=count,
        status=status,
        last_updated_at=evidence.occurred_at,
        evidence_ids=[*previous.evidence_ids[-19:], evidence.attempt_id],
    )

