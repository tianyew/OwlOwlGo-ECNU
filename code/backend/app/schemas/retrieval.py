"""Contracts shared by ingestion, retrieval and consuming agents."""

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class KnowledgeDocument(Contract):
    document_id: str = Field(min_length=1, max_length=120, pattern=r"^[a-zA-Z0-9_.-]+$")
    title: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=200_000)
    source: str = Field(min_length=1, max_length=1000)
    license: str = Field(min_length=1, max_length=200)
    content_version: int = Field(ge=1)
    review_status: Literal["draft", "approved"] = "draft"
    visibility: Literal["internal", "public"] = "internal"
    answer_visibility: Literal["teaching", "answer"] = "teaching"
    language: str = Field(default="zh", min_length=1, max_length=20)
    direction_ids: list[str] = Field(default_factory=list, max_length=20)
    knowledge_point_ids: list[str] = Field(default_factory=list, max_length=50)
    difficulty: int | None = Field(default=None, ge=1, le=6)


class IngestionResult(Contract):
    document_id: str
    content_version: int
    chunk_count: int
    chunk_ids: list[str]
    embedding_key: str


class RetrievalFilters(Contract):
    direction_id: str | None = Field(default=None, min_length=1, max_length=100)
    knowledge_point_id: str | None = Field(default=None, min_length=1, max_length=100)
    language: str | None = Field(default=None, min_length=1, max_length=20)
    difficulty: int | None = Field(default=None, ge=1, le=6)
    document_id: str | None = Field(default=None, min_length=1, max_length=120)


class RetrievalQuery(Contract):
    query: str = Field(min_length=1, max_length=2000)
    filters: RetrievalFilters = Field(default_factory=RetrievalFilters)
    top_k: int = Field(default=4, ge=1, le=10)
    max_context_chars: int = Field(default=6000, ge=200, le=16000)
    min_score: float = Field(default=0.0, ge=-1, le=1)


class RetrievalHit(Contract):
    chunk_id: str
    document_id: str
    title: str
    text: str
    source: str
    license: str
    content_version: int
    score: float

    @field_validator("score")
    @classmethod
    def finite_score(cls, value):
        if not math.isfinite(value):
            raise ValueError("score must be finite")
        return value


class RetrievalResult(Contract):
    hits: list[RetrievalHit]
    embedding_key: str
