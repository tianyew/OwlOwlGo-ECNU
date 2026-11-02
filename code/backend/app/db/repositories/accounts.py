"""Document-oriented account storage. Replace this adapter when choosing a database."""

import json
import os
import tempfile
from pathlib import Path
from typing import Protocol

from filelock import FileLock


class DuplicateUsername(Exception):
    pass


class AccountRepository(Protocol):
    def create_user(self, user: dict) -> None: ...
    def find_user(self, username: str) -> dict | None: ...
    def save_session(self, session: dict, now: int) -> None: ...
    def session_user(self, token_hash: str, now: int) -> dict | None: ...
    def delete_session(self, token_hash: str) -> None: ...


class JsonAccountRepository:
    """One local file; interprocess lock and atomic replacement prevent lost writes.

    Appropriate for a small, single-machine prototype, not a distributed database.
    A malformed existing file raises an error and is never silently overwritten.
    """

    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = FileLock(str(path) + ".lock", timeout=10)

    def _read(self) -> dict:
        if not self.path.exists():
            return {"schema_version": 1, "users": [], "sessions": []}
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if data.get("schema_version") != 1:
            raise ValueError("Unsupported account schema version")
        if not isinstance(data.get("users"), list) or not isinstance(data.get("sessions"), list):
            raise ValueError("Invalid account collections")
        return data

    def _write(self, data: dict) -> None:
        fd, name = tempfile.mkstemp(dir=self.path.parent, prefix=".accounts-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(data, stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self.path)
        finally:
            if os.path.exists(name):
                os.unlink(name)

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

    def save_session(self, session: dict, now: int) -> None:
        with self.lock:
            data = self._read()
            data["sessions"] = [s for s in data["sessions"] if s["expires_at"] > now]
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
