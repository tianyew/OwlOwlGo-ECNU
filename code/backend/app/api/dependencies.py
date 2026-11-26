"""Shared HTTP authentication and same-origin dependencies."""

import time
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import Depends, HTTPException, Request

from app.core.security import token_digest
from app.db.repositories.accounts import AccountRepository
from app.schemas.auth import PublicUser, public_user
from app.services.retrieval import IngestionService, RetrievalService

COOKIE = "owl_session"


def repository(request: Request) -> AccountRepository:
    return request.app.state.accounts


Repository = Annotated[AccountRepository, Depends(repository)]


def same_origin(request: Request):
    origin = request.headers.get("origin")
    # Browser requests without Origin still expose fetch metadata.
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(403, "请求来源无效，请从本站操作。")
    if origin:
        try:
            source = urlsplit(origin)
            target = urlsplit(str(request.base_url))
            valid = (
                source.scheme in {"http", "https"}
                and source.scheme == target.scheme
                and source.hostname == target.hostname
                and (source.port or (443 if source.scheme == "https" else 80))
                == (target.port or (443 if target.scheme == "https" else 80))
                and not source.username and not source.password
                and not source.path and not source.query and not source.fragment
            )
        except ValueError:
            valid = False
        if not valid:
            raise HTTPException(403, "请求来源无效，请从本站操作。")


def optional_user(request: Request, repo: Repository) -> PublicUser | None:
    token = request.cookies.get(COOKIE)
    user = repo.session_user(token_digest(token), int(time.time())) if token else None
    return public_user(user) if user else None


OptionalUser = Annotated[PublicUser | None, Depends(optional_user)]


def current_user(user: OptionalUser) -> PublicUser:
    if user is None:
        raise HTTPException(401, "请先登录。")
    return user


User = Annotated[PublicUser, Depends(current_user)]


def knowledge_editor(request: Request, user: User) -> PublicUser:
    allowed = request.app.state.settings.rag_ingest_user_ids
    if user.id not in {str(user_id) for user_id in allowed}:
        raise HTTPException(403, "当前账号没有知识库入库权限。")
    return user


KnowledgeEditor = Annotated[PublicUser, Depends(knowledge_editor)]


def ingestion_service(request: Request) -> IngestionService:
    service = request.app.state.ingestion
    if service is None:
        raise HTTPException(503, "知识库入库尚未启用。")
    return service


def retrieval_service(request: Request) -> RetrievalService:
    service = request.app.state.retrieval
    if service is None:
        raise HTTPException(503, "知识检索尚未启用。")
    return service
