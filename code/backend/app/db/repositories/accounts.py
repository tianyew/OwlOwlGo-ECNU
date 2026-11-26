"""Document-oriented account storage. Replace this adapter when choosing a database."""

import json
from typing import Protocol

from app.db.json_store import JsonFileStore


class DuplicateUsername(Exception):
    pass


class AccountRepository(Protocol):
    def create_user(self, user: dict) -> None: ...
    def find_user(self, username: str) -> dict | None: ...
    def save_session(self, session: dict, now: int, replace: str | None = None) -> None: ...
    def session_user(self, token_hash: str, now: int) -> dict | None: ...
    def delete_session(self, token_hash: str) -> None: ...
    def consume_auth_attempt(self, limits: dict[str, int], now: int, window: int) -> int: ...


class JsonAccountRepository(JsonFileStore):
    """One local file; interprocess lock and atomic replacement prevent lost writes.

    Appropriate for a small, single-machine prototype, not a distributed database.
    A malformed existing file raises an error and is never silently overwritten.
    """

    def _read(self) -> dict:
        if not self.path.exists():
            return {"schema_version": 1, "users": [], "sessions": []}
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if data.get("schema_version") != 1:
            raise ValueError("Unsupported account schema version")
        if not isinstance(data.get("users"), list) or not isinstance(data.get("sessions"), list):
            raise ValueError("Invalid account collections")
        return data

    def create_user(self, user: dict) -> None:
        with self.lock:
            data = self._read()
            if any(item["username"] == user["username"] for item in data["users"]):
                raise DuplicateUsername
            data["users"].append(user)
            self._write(data)

    def find_user(self, username: str) -> dict | None:
        with self.lock:
            return next((u for u in self._read()["users"] if u["username"] == username), None)

    def save_session(self, session: dict, now: int, replace: str | None = None) -> None:
        with self.lock:
            data = self._read()
            data["sessions"] = [
                s for s in data["sessions"] if s["expires_at"] > now and s["_id"] != replace
            ]
            data["sessions"].append(session)
            self._write(data)

    def session_user(self, token_hash: str, now: int) -> dict | None:
        with self.lock:
            data = self._read()
            session = next(
                (s for s in data["sessions"] if s["_id"] == token_hash and s["expires_at"] > now),
                None,
            )
            if session is None:
                return None
            return next((u for u in data["users"] if u["_id"] == session["user_id"]), None)

    def delete_session(self, token_hash: str) -> None:
        with self.lock:
            data = self._read()
            data["sessions"] = [s for s in data["sessions"] if s["_id"] != token_hash]
            self._write(data)

    def consume_auth_attempt(self, limits: dict[str, int], now: int, window: int) -> int:
        """Reserve an attempt before hashing; shared across workers and restarts.

        Fixed windows include successful attempts. Denied requests never extend
        a window. Keys are digests, so raw IPs/usernames are not stored here.
        """
        with self.lock:
            data = self._read()
            attempts = {
                key: value for key, value in data.get("auth_attempts", {}).items()
                if value["expires_at"] > now
            }
            retry_after = max(
                (attempts[key]["expires_at"] - now for key, limit in limits.items()
                 if key in attempts and attempts[key]["count"] >= limit),
                default=0,
            )
            if retry_after:
                return retry_after
            for key in limits:
                attempt = attempts.setdefault(key, {"count": 0, "expires_at": now + window})
                attempt["count"] += 1
            data["auth_attempts"] = attempts
            self._write(data)
            return 0
