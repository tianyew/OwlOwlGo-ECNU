"""Versioned progress contract; scores are derived on the server."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.content.catalog import get_quiz, validate_answers
from app.schemas.unit_quiz import UnitAnswer

Topic = Literal["travel", "daily", "campus", "poetry"]
Answer = Annotated[int, Field(strict=True, ge=0, le=3)]


class Quiz(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stage: Literal["intro", "quiz", "result"] = "intro"
    current: int = Field(default=0, ge=0, le=7)
    selected: Answer | None = None
    submitted: bool = False
    answers: list[Answer] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def consistent(self):
        if self.stage == "intro":
            valid = not self.answers and self.current == 0 and not self.submitted
        else:
            valid = len(self.answers) == self.current + int(self.submitted)
            if self.submitted:
                valid = valid and self.selected == self.answers[-1]
            if self.stage == "result":
                valid = valid and len(self.answers) == 8
        if not valid:
            raise ValueError("Inconsistent quiz state")
        return self


class PracticeAttempt(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answers: list[Annotated[int, Field(strict=True, ge=-1, le=2)]] = Field(
        default_factory=list, max_length=10
    )
    submitted: bool = False

    @model_validator(mode="after")
    def consistent(self):
        if self.submitted and (not self.answers or -1 in self.answers):
            raise ValueError("Complete all practice questions first")
        return self


class QuizDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content_version: Literal[1] = 1
    current: int = Field(default=0, strict=True, ge=0, le=9)
    answers: list[UnitAnswer] = Field(default_factory=list, max_length=10)


class LearningState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    onboarding_complete: bool = False
    content_version: Literal[1] = 1
    stage: Literal["assessment", "topics", "plan"] = "assessment"
    quiz: Quiz = Field(default_factory=Quiz)
    topic: Topic | None = None
    completed: dict[Topic, list[Annotated[int, Field(strict=True, ge=0, le=4)]]] = Field(
        default_factory=dict
    )
    checks: dict[str, PracticeAttempt] = Field(default_factory=dict, max_length=20)
    posttests: dict[Topic, PracticeAttempt] = Field(default_factory=dict)
    drafts: dict[str, QuizDraft] = Field(default_factory=dict, max_length=25)

    @model_validator(mode="after")
    def consistent(self):
        for quiz_id, draft in self.drafts.items():
            try:
                quiz = get_quiz(quiz_id)
                answers = {a.question_id: a.selected_index for a in draft.answers}
                validate_answers(quiz_id, answers, complete=False)
                if len(answers) != len(draft.answers) or draft.current >= len(quiz["questions"]):
                    raise ValueError("Invalid draft")
            except KeyError as exc:
                raise ValueError("Invalid quiz") from exc
        if self.onboarding_complete and (self.quiz.stage != "result" or self.topic is None):
            raise ValueError("Complete assessment and choose a plan first")
        if self.stage != "assessment" and self.quiz.stage != "result":
            raise ValueError("Finish assessment first")
        if self.stage == "plan" and self.topic is None:
            raise ValueError("Select a topic first")
        if any(
            len(items) != len(set(items)) or len(items) > 5 for items in self.completed.values()
        ):
            raise ValueError("Invalid completed units")
        for key, attempt in self.checks.items():
            if key not in {
                f"{topic}:{index}"
                for topic in ("travel", "daily", "campus", "poetry")
                for index in range(5)
            } or len(attempt.answers) not in (0, 2):
                raise ValueError("Invalid unit practice")
            if attempt.submitted and len(attempt.answers) != 2:
                raise ValueError("Incomplete unit practice")
        for attempt in self.posttests.values():
            if len(attempt.answers) not in (0, 10):
                raise ValueError("Invalid post-test")
            if attempt.submitted and len(attempt.answers) != 10:
                raise ValueError("Incomplete post-test")
        return self


class SaveProgress(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=0)
    state: LearningState
