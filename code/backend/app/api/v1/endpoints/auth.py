"""Real registration/login backed by a replaceable document repository."""

import secrets
import time
from datetime import UTC, datetime
from typing import Annotated
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.security import hash_password, token_digest, verify_password
from app.db.repositories.accounts import AccountRepository, DuplicateUsername

COOKIE = "owl_session"
SESSION_SECONDS = 7 * 24 * 60 * 60
# Missing-user logins still perform a password verification.
DUMMY_HASH = hash_password(secrets.token_urlsafe(32))
router = APIRouter(prefix="/api/v1/auth", tags=["accounts"])


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=3, max_length=32, pattern=r"^[a-z0-9_]+$")
    password: str = Field(min_length=1, max_length=128)

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class Registration(Credentials):
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=40)

    @field_validator("display_name", mode="before")
    @classmethod
    def normalize_name(cls, value):
        return value.strip() if isinstance(value, str) else value


class PublicUser(BaseModel):
    id: str
    username: str
    display_name: str


def public_user(user: dict) -> PublicUser:
    return PublicUser(id=user["_id"], username=user["username"], display_name=user["display_name"])


def repository(request: Request) -> AccountRepository:
    return request.app.state.accounts


Repository = Annotated[AccountRepository, Depends(repository)]


def same_origin(request: Request):
    origin = request.headers.get("origin")
    if origin and urlsplit(origin).netloc != request.headers.get("host"):
        raise HTTPException(403, "请求来源无效，请从本站操作。")


def new_session(user: dict, request: Request, response: Response, repo: AccountRepository):
    token = secrets.token_urlsafe(32)
    now = int(time.time())
    repo.save_session(
        {
            "_id": token_digest(token),
            "user_id": user["_id"],
            "created_at": now,
            "expires_at": now + SESSION_SECONDS,
        },
        now,
    )
    # Rotate this browser's prior session on login / registration.
    old = request.cookies.get(COOKIE)
    if old:
        repo.delete_session(token_digest(old))
    response.set_cookie(
        COOKIE,
        token,
        max_age=SESSION_SECONDS,
        httponly=True,
        secure=request.app.state.secure_cookies,
        samesite="strict",
        path="/",
    )


@router.post(
    "/register", response_model=PublicUser, status_code=201, dependencies=[Depends(same_origin)]
)
def register(body: Registration, request: Request, response: Response, repo: Repository):
    user = {
        "_id": str(uuid4()),
        "username": body.username,
        "display_name": body.display_name,
        "password_hash": hash_password(body.password),
        "created_at": datetime.now(UTC).isoformat(),
        "schema_version": 1,
    }
    try:
        repo.create_user(user)
    except DuplicateUsername:
        raise HTTPException(409, "该账号已被注册，请更换账号或登录。") from None
    new_session(user, request, response, repo)
    return public_user(user)


@router.post("/login", response_model=PublicUser, dependencies=[Depends(same_origin)])
def login(body: Credentials, request: Request, response: Response, repo: Repository):
    user = repo.find_user(body.username)
    valid = verify_password(body.password, user["password_hash"] if user else DUMMY_HASH)
    if not valid or user is None:
        raise HTTPException(401, "账号或密码不正确。")
    new_session(user, request, response, repo)
    return public_user(user)


@router.get("/me", response_model=PublicUser)
def me(request: Request, repo: Repository):
    token = request.cookies.get(COOKIE)
    user = repo.session_user(token_digest(token), int(time.time())) if token else None
    if user is None:
        raise HTTPException(401, "请先登录。")
    return public_user(user)


@router.post("/logout", status_code=204, dependencies=[Depends(same_origin)])
def logout(request: Request, response: Response, repo: Repository):
    token = request.cookies.get(COOKIE)
    if token:
        repo.delete_session(token_digest(token))
    response.delete_cookie(
        COOKIE, path="/", httponly=True, secure=request.app.state.secure_cookies, samesite="strict"
    )
