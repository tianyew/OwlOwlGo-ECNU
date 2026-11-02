"""Assessment review agent: prompt, output contract and evidence checks."""

from datetime import UTC, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.integrations.llm.deepseek import AnalysisUnavailable, DeepSeekClient
from app.integrations.llm.prompts.assessment import PROMPT_VERSION, SYSTEM_PROMPT

ShortText = Annotated[str, Field(min_length=1, max_length=300)]
QuestionId = Annotated[str, Field(min_length=1, max_length=40)]


class QuestionFeedback(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question_id: QuestionId
    observation: ShortText
    suggestion: ShortText


class PracticeTask(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: ShortText
    reason: ShortText
    question_ids: list[QuestionId] = Field(min_length=1, max_length=8)
    activity: ShortText
    success_criterion: ShortText


class AnalysisContent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str = Field(min_length=1, max_length=600)
    strengths: list[ShortText] = Field(max_length=3)
    focus_areas: list[ShortText] = Field(max_length=3)
    next_steps: list[ShortText] = Field(min_length=2, max_length=3)
    question_feedback: list[QuestionFeedback] = Field(max_length=8)
    practice_tasks: list[PracticeTask] = Field(min_length=2, max_length=3)

    def check_evidence(self, evidence: dict):
        items = evidence["items"]
        ids = {item["question_id"] for item in items}
        wrong = {item["question_id"] for item in items if not item["is_correct"]}
        feedback = [item.question_id for item in self.question_feedback]
        if set(feedback) != wrong or len(feedback) != len(wrong):
            raise ValueError("Feedback must cover each wrong answer exactly once")
        if any(not set(task.question_ids) <= ids for task in self.practice_tasks):
            raise ValueError("Unknown question reference")
        if len(wrong) == len(items) and self.strengths:
            raise ValueError("Do not invent demonstrated strengths for all wrong answers")
        if not wrong and self.focus_areas:
            raise ValueError("Do not invent weaknesses for a perfect submission")


class AssessmentAgent:
    agent_id = "assessment_review"
    prompt_version = PROMPT_VERSION

    def __init__(self, client: DeepSeekClient):
        self.client = client

    def analyze(self, evidence: dict) -> dict:
        try:
            content = self.client.complete(SYSTEM_PROMPT, evidence, max_tokens=4000)
            result = AnalysisContent.model_validate_json(content)
            result.check_evidence(evidence)
        except (ValueError, KeyError, TypeError):
            raise AnalysisUnavailable("前测分析暂不可用，请稍后重试；学习进度已保留。") from None
        return {
            "agent_id": self.agent_id,
            "provider": "deepseek",
            "prompt_version": self.prompt_version,
            "model": self.client.settings.deepseek_model,
            "created_at": datetime.now(UTC).isoformat(),
            **result.model_dump(),
        }
