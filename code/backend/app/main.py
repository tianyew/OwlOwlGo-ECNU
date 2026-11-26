"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.router import router
from app.core.config import Settings
from app.core.logging import configure_logging, request_route
from app.core.security import hash_password
from app.db.repositories.accounts import DuplicateUsername, JsonAccountRepository
from app.db.repositories.learning import JsonLearningRepository
from app.db.repositories.postgres_accounts import PostgresAccountRepository
from app.db.session import check_schema, database_engine
from app.integrations.llm.deepseek import DeepSeekClient
from app.services.agents.assessment import AssessmentAgent
from app.services.agents.dispatcher import AgentDispatcher

logger = logging.getLogger(__name__)


def create_app(data_path: Path | None = None, settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    configure_logging(settings)
    url = settings.database_url.get_secret_value()
    # An explicit file path is the isolated JSON fixture/local compatibility mode.
    engine = database_engine(url) if url and data_path is None else None

    @asynccontextmanager
    async def lifespan(app):
        try:
            if engine is not None:
                check_schema(engine)
                seed_demo_account(app)
            logger.info("application_started")
            yield
        except Exception:
            logger.exception("application_lifespan_failed")
            raise
        finally:
            if engine is not None:
                engine.dispose()
            logger.info("application_stopped")

    application = FastAPI(title="OwlOwlGo API", version="0.1.0", lifespan=lifespan)
    application.state.settings = settings
    application.state.accounts = (
        PostgresAccountRepository(engine) if engine is not None
        else JsonAccountRepository(data_path or settings.owl_account_file)
    )
    if engine is None:
        seed_demo_account(application)
    application.state.secure_cookies = settings.owl_secure_cookies
    application.state.learning = JsonLearningRepository(
        settings.owl_learning_file
        or (data_path or settings.owl_account_file).with_name("learning.json")
    )
    application.state.agents = AgentDispatcher(
        [AssessmentAgent(DeepSeekClient(settings))]
    )
    application.include_router(router)

    @application.exception_handler(SQLAlchemyError)
    async def database_error(request, exc):
        logger.error(
            "database_error method=%s route=%s", request.method, request_route(request),
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        return JSONResponse(status_code=503, content={"detail": "账号数据库暂不可用，请稍后重试。"})

    @application.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # Never echo submitted password values in validation errors.
        if request.url.path.startswith("/api/v1/learning/"):
            return JSONResponse(
                status_code=422, content={"detail": "学习请求格式不正确，请检查题目与答案后重试。"}
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
        started = perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "request_failed method=%s route=%s status=500 duration_ms=%.2f",
                request.method, request_route(request), (perf_counter() - started) * 1000,
            )
            raise
        log = logger.error if response.status_code >= 500 else logger.info
        log(
            "request_completed method=%s route=%s status=%s duration_ms=%.2f",
            request.method, request_route(request), response.status_code,
            (perf_counter() - started) * 1000,
        )
        if request.url.path.startswith("/api/v1/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    return application


def seed_demo_account(application):
    # Seed once for the local demo; never reset an existing account on restart.
    if application.state.settings.owl_seed_demo_account:
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


app = create_app()
