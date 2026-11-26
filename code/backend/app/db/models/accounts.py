"""PostgreSQL account schema, migration version 1."""

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    Uuid,
)

metadata = MetaData()
versions = Table("auth_schema_versions", metadata, Column("version", Integer, primary_key=True))
users = Table(
    "auth_users", metadata,
    Column("id", Uuid(as_uuid=False), primary_key=True),
    Column("username", String(32), nullable=False, unique=True),
    Column("display_name", String(40), nullable=False),
    Column("password_hash", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("username ~ '^[a-z0-9_]{3,32}$'", name="auth_username_format"),
    CheckConstraint("length(trim(display_name)) > 0", name="auth_display_name_nonempty"),
)
sessions = Table(
    "auth_sessions", metadata,
    Column("token_hash", String(64), primary_key=True),
    Column("user_id", Uuid(as_uuid=False), ForeignKey("auth_users.id", ondelete="CASCADE"),
           nullable=False, index=True),
    Column("created_at", BigInteger, nullable=False),
    Column("expires_at", BigInteger, nullable=False, index=True),
    CheckConstraint("expires_at > created_at", name="auth_session_lifetime"),
)
attempts = Table(
    "auth_attempts", metadata,
    Column("key", String(64), primary_key=True),
    Column("count", Integer, nullable=False),
    Column("expires_at", BigInteger, nullable=False, index=True),
    CheckConstraint("count >= 0", name="auth_attempt_count"),
)
