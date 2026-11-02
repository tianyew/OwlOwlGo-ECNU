"""FastAPI application entry point."""

import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.v1.endpoints.auth import router
from app.api.v1.endpoints.learning import router as learning_router
from app.core.config import Settings
from app.core.security import hash_password
from app.db.repositories.accounts import DuplicateUsername, JsonAccountRepository
from app.db.repositories.learning import JsonLearningRepository
from app.integrations.llm.deepseek import DeepSeekClient
from app.services.agents.assessment import AssessmentAgent
from app.services.agents.dispatcher import AgentDispatcher


def create_app(data_path: Path | None = None, settings: Settings | None = None) -> FastAPI:
    application = FastAPI(title="OwlOwlGo API", version="0.1.0")
    default = Path(__file__).resolve().parents[1] / "local-data" / "accounts.json"
    application.state.accounts = JsonAccountRepository(
        data_path or Path(os.environ.get("OWL_ACCOUNT_FILE", str(default)))
    )
    # Seed once for the local demo; never reset an existing account on restart.
    if os.environ.get("OWL_SEED_DEMO_ACCOUNT", "true").lower() == "true":
        repo = application.state.accounts
        if repo.find_user("admin") is None:
            try:
                repo.create_user(
                    {
                        "_id": str(uuid4()),
                        "username": "admin",
                        "display_name": "演示账号",
                        "password_hash": hash_password("admin"),
                        "created_at": datetime.now(UTC).isoformat(),
                        "schema_version": 1,
                    }
                )
            except DuplicateUsername:
                pass  # Another worker already created the same default account.
    application.state.secure_cookies = (
        os.environ.get("OWL_SECURE_COOKIES", "false").lower() == "true"
    )
    application.state.learning = JsonLearningRepository(
        application.state.accounts.path.with_name("learning.json")
    )
    application.state.agents = AgentDispatcher(
        [AssessmentAgent(DeepSeekClient(settings or Settings()))]
    )
    application.include_router(router)
    application.include_router(learning_router)

    @application.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # Never echo submitted password values in validation errors.
        if request.url.path.startswith("/api/v1/learning/"):
            return JSONResponse(
                status_code=422, content={"detail": "学习进度格式不正确，请重新加载。"}
            )
        return JSONResponse(
            status_code=422,
            content={
                "detail": (
                    "请检查账号（3–32 位字母、数字或下划线）、"
                    "密码（注册时 8–128 位，登录时不能为空）和昵称（1–40 位）。"
                )
            },
        )

    @application.middleware("http")
    async def no_auth_cache(request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api/v1/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    return application


app = create_app()
