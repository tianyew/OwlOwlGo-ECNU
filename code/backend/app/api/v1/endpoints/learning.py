"""Content, authoritative assessment submissions, profiles and AI feedback."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.v1.endpoints.auth import PublicUser, me, repository, same_origin
from app.db.repositories.learning import (
    ProgressConflict,
    UnitSubmissionConflict,
    analysis_source,
    latest_results,
)
from app.domain.content.catalog import CONTENT_VERSION, QUIZZES, get_quiz, public_catalog, public_questions
from app.domain.learner.profile import formal_records, latest_wrong
from app.integrations.llm.deepseek import AnalysisUnavailable
from app.schemas.learning import SaveProgress, evidence
from app.schemas.unit_quiz import ResetAssessment, SubmitUnitQuiz

router = APIRouter(prefix="/api/v1/learning", tags=["learning"])
User = Annotated[PublicUser, Depends(me)]


def optional_user(request: Request):
    try:
        return me(request, repository(request))
    except HTTPException as exc:
        if exc.status_code != 401:
            raise
        return None


OptionalUser = Annotated[PublicUser | None, Depends(optional_user)]


def conflict(exc):
    return HTTPException(409, str(exc) or "另一页面更新了学习进度，请重新加载已保存进度后继续。")


@router.get("/curriculum")
def get_curriculum():
    return public_catalog()


@router.get("/progress")
def get_progress(request: Request, user: User):
    return request.app.state.learning.public_progress(user.id)


@router.put("/progress", dependencies=[Depends(same_origin)])
def save_progress(body: SaveProgress, request: Request, user: User):
    try:
        repo = request.app.state.learning
        return repo.without_unit_history(repo.save(user.id, body.state.model_dump(), body.revision))
    except ProgressConflict as exc:
        raise conflict(exc) from None


def quiz_payload(quiz_id, request, user):
    try:
        quiz = get_quiz(quiz_id)
    except KeyError:
        raise HTTPException(404, "测验不存在。") from None
    record = request.app.state.learning.get(user.id) if user else None
    return {
        **{key: quiz[key] for key in ("id", "kind", "title", "topic", "unit_index")},
        "content_version": CONTENT_VERSION,
        "questions": public_questions(quiz_id),
        "result": latest_results(record).get(quiz_id) if record else None,
        "draft": record["state"].get("drafts", {}).get(quiz_id) if record else None,
        "unit_completed": bool(
            record
            and quiz["kind"] == "unit"
            and quiz["unit_index"] in record["state"]["completed"][quiz["topic"]]
        ),
    }


@router.get("/quizzes/{quiz_id}")
def read_quiz(quiz_id: str, request: Request, user: OptionalUser):
    return quiz_payload(quiz_id, request, user)


def submit(quiz_id, body, request, user):
    answers = {item.question_id: item.selected_index for item in body.answers}
    if len(answers) != len(body.answers):
        raise HTTPException(422, "请勿重复提交同一道题。")
    repo = request.app.state.learning
    try:
        response = repo.submit_quiz(
            user.id, quiz_id, str(body.submission_id), body.content_version, answers, body.revision
        )
    except KeyError:
        raise HTTPException(404, "测验不存在。") from None
    except (ProgressConflict, UnitSubmissionConflict) as exc:
        raise conflict(exc) from None
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    response["progress"] = repo.without_unit_history(response["progress"])
    return response


@router.post("/quizzes/{quiz_id}/submissions", dependencies=[Depends(same_origin)])
def submit_quiz(quiz_id: str, body: SubmitUnitQuiz, request: Request, user: User):
    return submit(quiz_id, body, request, user)


# Preserve the pilot URLs while covering all twenty units with the same rules.
@router.get("/units/{topic}/{index}/quiz")
def get_unit_quiz(topic: str, index: int, request: Request, user: User):
    return quiz_payload(f"unit-{topic}-{index}", request, user)


@router.post("/units/{topic}/{index}/submissions", dependencies=[Depends(same_origin)])
def submit_unit_quiz(topic: str, index: int, body: SubmitUnitQuiz, request: Request, user: User):
    return submit(f"unit-{topic}-{index}", body, request, user)


@router.post("/assessment/reset", dependencies=[Depends(same_origin)])
def reset_assessment(body: ResetAssessment, request: Request, user: User):
    repo = request.app.state.learning
    try:
        return repo.without_unit_history(repo.reset_assessment(user.id, body.revision))
    except ProgressConflict as exc:
        raise conflict(exc) from None


@router.get("/posttest-history")
def read_posttest_history(request: Request, user: User):
    record = request.app.state.learning.get(user.id)
    return [
        {key: result[key] for key in ("submission_id", "topic", "score", "created_at")}
        for result in reversed(formal_records(record["submissions"]))
        if result["kind"] == "posttest"
    ]


@router.get("/submissions/{submission_id}")
def read_submission(submission_id: str, request: Request, user: User):
    repo = request.app.state.learning
    record = repo.get(user.id)
    result = record["submissions"].get(submission_id)
    if result is None or result.get("provenance") == "legacy_answers":
        raise HTTPException(404, "找不到这次正式提交。")
    if result["kind"] != "posttest":
        raise HTTPException(422, "这次提交不是方向后测。")
    topic = result["topic"]
    progress = repo.without_unit_history(record)
    return {
        "result": result,
        "topic_completion": progress["topic_completion"].get(topic, False),
        "completed_units": len(record["state"]["completed"].get(topic, [])),
        "profile": progress["profile"],
    }


@router.get("/review-queue")
def read_review_queue(request: Request, user: User):
    record = request.app.state.learning.get(user.id)
    return latest_wrong(record["submissions"], QUIZZES)


@router.get("/profile")
def get_profile(request: Request, user: User):
    return request.app.state.learning.public_progress(user.id)["profile"]


@router.post("/analysis", dependencies=[Depends(same_origin)])
def analyze(request: Request, user: User):
    repo = request.app.state.learning
    record = repo.get(user.id)
    if "assessment" not in latest_results(record):
        raise HTTPException(400, "请先完成前测，再进行学习分析。")
    if record["analysis"] is not None:
        return record["analysis"]
    try:
        result = request.app.state.agents.run(
            "assessment.report_requested", evidence(record["state"])
        )
        return repo.save_analysis(user.id, analysis_source(record), result)
    except AnalysisUnavailable as exc:
        raise HTTPException(503, str(exc)) from None
    except ProgressConflict:
        raise HTTPException(409, "分析期间学习进度发生变化，请根据最新进度重新分析。") from None
