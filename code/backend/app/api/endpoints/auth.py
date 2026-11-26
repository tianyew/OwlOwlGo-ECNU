"""Real registration/login backed by a replaceable document repository."""

import secrets
import time
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.api.dependencies import COOKIE, Repository, User, same_origin
from app.core.security import hash_password, token_digest, verify_password
from app.db.repositories.accounts import AccountRepository, DuplicateUsername
from app.schemas.auth import Credentials, PublicUser, Registration, public_user

# Missing-user logins still perform a password verification.
DUMMY_HASH = hash_password(secrets.token_urlsafe(32))
router = APIRouter(prefix="/api/v1/auth", tags=["accounts"])


def throttle(request: Request, repo: AccountRepository, action: str, username: str = ""):
    settings = request.app.state.settings
    # Trust only the server-resolved client, never arbitrary forwarded headers.
    address = request.client.host if request.client else "unknown"
    limits = {
        token_digest(f"{action}:ip:{address}"): (
            settings.owl_login_ip_limit if action == "login" else settings.owl_register_ip_limit
        )
    }
    if action == "login":
        limits[token_digest(f"login:account:{username}")] = settings.owl_login_account_limit
    retry = repo.consume_auth_attempt(limits, int(time.time()), settings.owl_auth_window_seconds)
    if retry:
        raise HTTPException(
            429, f"操作过于频繁，请在 {retry} 秒后重试。", headers={"Retry-After": str(retry)}
        )


def new_session(user: dict, request: Request, response: Response, repo: AccountRepository):
    token = secrets.token_urlsafe(32)
    now = int(time.time())
    lifetime = request.app.state.settings.owl_session_seconds
    old = request.cookies.get(COOKIE)
    repo.save_session(
        {
            "_id": token_digest(token),
            "user_id": user["_id"],
            "created_at": now,
            "expires_at": now + lifetime,
        },
        now,
        replace=token_digest(old) if old else None,
    )
    response.set_cookie(
        COOKIE,
        token,
        max_age=lifetime,
        httponly=True,
        secure=request.app.state.secure_cookies,
        samesite="strict",
        path="/",
    )


@router.post(
    "/register", response_model=PublicUser, status_code=201, dependencies=[Depends(same_origin)]
)
def register(body: Registration, request: Request, response: Response, repo: Repository):
    throttle(request, repo, "register")
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
    throttle(request, repo, "login", body.username)
    user = repo.find_user(body.username)
    valid = verify_password(body.password, user["password_hash"] if user else DUMMY_HASH)
    if not valid or user is None:
        raise HTTPException(401, "账号或密码不正确。")
    new_session(user, request, response, repo)
    return public_user(user)


@router.get("/me", response_model=PublicUser)
def me(user: User):
    return user


@router.post("/logout", status_code=204, dependencies=[Depends(same_origin)])
def logout(request: Request, response: Response, repo: Repository):
    token = request.cookies.get(COOKIE)
    if token:
        repo.delete_session(token_digest(token))
    response.delete_cookie(
        COOKIE, path="/", httponly=True, secure=request.app.state.secure_cookies, samesite="strict"
    )
