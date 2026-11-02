"""Authenticated learning progress and read-only AI analysis."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.v1.endpoints.auth import PublicUser, me, same_origin
from app.db.repositories.learning import ProgressConflict
from app.integrations.llm.deepseek import AnalysisUnavailable
from app.schemas.learning import SaveProgress, evidence, fingerprint

router = APIRouter(prefix="/api/v1/learning", tags=["learning"])
User = Annotated[PublicUser, Depends(me)]


@router.get("/progress")
def get_progress(request: Request, user: User):
    return request.app.state.learning.get(user.id)


@router.put("/progress", dependencies=[Depends(same_origin)])
def save_progress(body: SaveProgress, request: Request, user: User):
    try:
        return request.app.state.learning.save(user.id, body.state.model_dump(), body.revision)
    except ProgressConflict:
        raise HTTPException(409, "另一页面更新了学习进度，请重新加载已保存进度后继续。") from None


@router.post("/analysis", dependencies=[Depends(same_origin)])
def analyze(request: Request, user: User):
    repo = request.app.state.learning
    record = repo.get(user.id)
    if record["state"]["quiz"]["stage"] != "result":
        raise HTTPException(400, "请先完成前测，再进行学习分析。")
    if record["analysis"] is not None:
        return record["analysis"]
    try:
        result = request.app.state.agents.run(
            "assessment.report_requested", evidence(record["state"])
        )
        return repo.save_analysis(user.id, fingerprint(record["state"]), result)
    except AnalysisUnavailable as exc:
        raise HTTPException(503, str(exc)) from None
    except ProgressConflict:
        raise HTTPException(409, "分析期间学习进度发生变化，请根据最新进度重新分析。") from None
