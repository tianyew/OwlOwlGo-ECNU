"""Run with python -m app.db.manage: init, import-json, or cleanup."""

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy import delete, or_, select, text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import Settings
from app.db.models.accounts import attempts, sessions, users
from app.db.repositories.postgres_accounts import user_values
from app.db.session import check_schema, database_engine, initialize_schema


class ImportedUser(BaseModel):
    id: UUID = Field(alias="_id")
    username: str = Field(pattern=r"^[a-z0-9_]{3,32}$")
    display_name: str = Field(min_length=1, max_length=40)
    password_hash: str = Field(pattern=r"^scrypt\$16384\$8\$1\$[0-9a-f]{32}\$[0-9a-f]{128}$")
    created_at: datetime
    schema_version: Literal[1]

    @field_validator("created_at")
    @classmethod
    def timezone_required(cls, value):
        if value.tzinfo is None:
            raise ValueError("created_at must include a timezone")
        return value

    @field_validator("display_name")
    @classmethod
    def nonempty_name(cls, value):
        if not value.strip():
            raise ValueError("display_name must not be blank")
        return value


def import_json(engine, path: Path, *, dry_run: bool = False) -> tuple[int, int]:
    """Keep UUIDs/hashes; never overwrite users, import sessions, or edit the source."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or not isinstance(data.get("users"), list):
        raise ValueError("Unsupported JSON account format")
    try:
        records = [user_values(ImportedUser.model_validate(user).model_dump(
            mode="json", by_alias=True,
        )) for user in data["users"]]
    except ValidationError:
        # Do not print hashes or account contents in validation errors.
        raise ValueError("Invalid account fields in source JSON; no records imported") from None
    added = skipped = 0
    with engine.begin() as connection:
        connection.execute(text("LOCK TABLE auth_users IN SHARE ROW EXCLUSIVE MODE"))
        for record in records:
            existing = connection.execute(select(users).where(or_(
                users.c.id == record["id"], users.c.username == record["username"],
            ))).mappings().all()
            if existing:
                if len(existing) != 1 or dict(existing[0]) != record:
                    raise ValueError("Account ID/username conflict; entire import rolled back")
                skipped += 1
            else:
                connection.execute(users.insert().values(**record))
                added += 1
        if dry_run:
            connection.rollback()
    return added, skipped


def cleanup(engine, now: int) -> None:
    with engine.begin() as connection:
        # Maintenance serializes with counter updates, including their first inserts.
        connection.execute(text("LOCK TABLE auth_attempts IN SHARE ROW EXCLUSIVE MODE"))
        connection.execute(delete(attempts).where(attempts.c.expires_at <= now))
        connection.execute(delete(sessions).where(sessions.c.expires_at <= now))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="Apply initial account schema migration")
    importer = commands.add_parser("import-json", help="Import legacy users; omit old sessions")
    importer.add_argument("path", type=Path)
    importer.add_argument("--dry-run", action="store_true")
    commands.add_parser("cleanup", help="Remove expired sessions and authentication counters")
    args = parser.parse_args()
    url = Settings().database_url.get_secret_value()
    if not url:
        parser.exit(1, "Set DATABASE_URL in code/backend/.env first.\n")
    engine = None
    try:
        engine = database_engine(url)
        if args.command == "init":
            initialize_schema(engine)
            print("Account schema is ready (version 1).")
        else:
            check_schema(engine)
            if args.command == "import-json":
                added, skipped = import_json(engine, args.path, dry_run=args.dry_run)
                label = "Dry run" if args.dry_run else "Import"
                print(f"{label}: {added} new, {skipped} unchanged.")
                print("Existing user IDs preserved. Old sessions are not imported; sign in again.")
            else:
                cleanup(engine, int(time.time()))
                print("Expired sessions and counters removed.")
    except SQLAlchemyError:
        parser.exit(1, "Database operation failed; check connectivity, credentials and schema.\n")
    except (ValueError, OSError, RuntimeError) as exc:
        parser.exit(1, f"{exc}\n")
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    main()
