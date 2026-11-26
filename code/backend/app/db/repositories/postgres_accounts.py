"""PostgreSQL implementation of the existing account repository contract."""

from datetime import datetime

from sqlalchemy import delete, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from app.db.models.accounts import attempts, sessions, users
from app.db.repositories.accounts import DuplicateUsername


def user_values(user: dict) -> dict:
    return {
        "id": user["_id"], "username": user["username"], "display_name": user["display_name"],
        "password_hash": user["password_hash"],
        "created_at": datetime.fromisoformat(user["created_at"]),
    }


def user_document(row) -> dict | None:
    if row is None:
        return None
    return {
        "_id": row["id"], "username": row["username"], "display_name": row["display_name"],
        "password_hash": row["password_hash"], "created_at": row["created_at"].isoformat(),
        "schema_version": 1,
    }


class PostgresAccountRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    def create_user(self, user: dict) -> None:
        try:
            with self.engine.begin() as connection:
                connection.execute(users.insert().values(**user_values(user)))
        except IntegrityError as exc:
            if getattr(exc.orig, "sqlstate", None) == "23505" and (
                getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
                == "auth_users_username_key"
            ):
                raise DuplicateUsername from None
            raise

    def find_user(self, username: str) -> dict | None:
        with self.engine.connect() as connection:
            row = connection.execute(select(users).where(users.c.username == username))
            return user_document(row.mappings().first())

    def save_session(self, session: dict, now: int, replace: str | None = None) -> None:
        with self.engine.begin() as connection:
            connection.execute(delete(sessions).where(or_(
                sessions.c.expires_at <= now, sessions.c.token_hash == replace,
            )))
            connection.execute(sessions.insert().values(
                token_hash=session["_id"], user_id=session["user_id"],
                created_at=session["created_at"], expires_at=session["expires_at"],
            ))

    def session_user(self, token_hash: str, now: int) -> dict | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                select(users).join(sessions, sessions.c.user_id == users.c.id).where(
                    sessions.c.token_hash == token_hash, sessions.c.expires_at > now,
                )
            )
            return user_document(row.mappings().first())

    def delete_session(self, token_hash: str) -> None:
        with self.engine.begin() as connection:
            connection.execute(delete(sessions).where(sessions.c.token_hash == token_hash))

    def consume_auth_attempt(self, limits: dict[str, int], now: int, window: int) -> int:
        with self.engine.begin() as connection:
            counters = {}
            # Lock in a stable order, including first insertion, to avoid deadlocks.
            for key in sorted(limits):
                connection.execute(insert(attempts).values(
                    key=key, count=0, expires_at=now + window,
                ).on_conflict_do_nothing(index_elements=[attempts.c.key]))
                row = connection.execute(
                    select(attempts).where(attempts.c.key == key).with_for_update()
                ).mappings().one()
                counters[key] = dict(row) if row["expires_at"] > now else {
                    "key": key, "count": 0, "expires_at": now + window,
                }
            retry = max((
                value["expires_at"] - now for key, value in counters.items()
                if value["count"] >= limits[key]
            ), default=0)
            if retry:
                return retry
            for key, value in counters.items():
                connection.execute(update(attempts).where(attempts.c.key == key).values(
                    count=value["count"] + 1, expires_at=value["expires_at"],
                ))
            return 0
