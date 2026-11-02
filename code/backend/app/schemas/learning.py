"""Versioned progress contract; scores are derived on the server."""

import hashlib
import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.integrations.llm.prompts.assessment import PROMPT_VERSION

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


class LearningState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    onboarding_complete: bool = False
    content_version: Literal[1] = 1
    stage: Literal["assessment", "topics", "plan"] = "assessment"
    quiz: Quiz = Field(default_factory=Quiz)
    topic: Topic | None = None
    completed: dict[Topic, list[Annotated[int, Field(strict=True, ge=0, le=2)]]] = Field(
        default_factory=dict
    )

    @model_validator(mode="after")
    def consistent(self):
        if self.onboarding_complete and (self.quiz.stage != "result" or self.topic is None):
            raise ValueError("Complete assessment and choose a plan first")
        if self.stage != "assessment" and self.quiz.stage != "result":
            raise ValueError("Finish assessment first")
        if self.stage == "plan" and self.topic is None:
            raise ValueError("Select a topic first")
        if any(
            len(items) != len(set(items)) or len(items) > 3 for items in self.completed.values()
        ):
            raise ValueError("Invalid completed units")
        return self


class SaveProgress(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=0)
    state: LearningState


# Same fixed demo question order as frontend/features/phonetics/questions.ts.
ITEMS = json.loads(
    (Path(__file__).resolve().parents[1] / "domain/learner/assessment_items.json").read_text(
        encoding="utf-8"
    )
)
KEY = [item["answer"] for item in ITEMS]
CATEGORIES = [("拼音基础", [0, 1]), ("四声辨识", [2, 3, 4]), ("基础变调", [5, 6, 7])]
TOPICS = {"travel": "旅游出行", "daily": "日常生活", "campus": "校园交流", "poetry": "古诗入门"}


def evidence(state: dict) -> dict:
    answers = state["quiz"]["answers"]
    return {
        "prompt_version": PROMPT_VERSION,
        "items": [
            {
                "question_id": q["id"],
                "knowledge_point": q["category"],
                "prompt": q["prompt"],
                "example": q["example"],
                "options": q["options"],
                "selected_index": answers[i],
                "selected_answer": q["options"][answers[i]],
                "correct_index": q["answer"],
                "correct_answer": q["options"][q["answer"]],
                "is_correct": answers[i] == q["answer"],
                "explanation": q["explanation"],
            }
            for i, q in enumerate(ITEMS)
            if i < len(answers)
        ],
        "score": int(sum(a == KEY[i] for i, a in enumerate(answers)) / len(KEY) * 100 + 0.5),
        "scope": "固定8题拼音与声调文字辨识，不代表正式汉语等级或口语水平",
        "answered": len(answers),
        "correct": sum(a == KEY[i] for i, a in enumerate(answers)),
        "dimensions": [
            {
                "name": name,
                "total": len(indices),
                "correct": sum(i < len(answers) and answers[i] == KEY[i] for i in indices),
            }
            for name, indices in CATEGORIES
        ],
    }


def fingerprint(state: dict) -> str:
    return hashlib.sha256(json.dumps(evidence(state), sort_keys=True).encode()).hexdigest()
