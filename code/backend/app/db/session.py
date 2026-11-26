"""PostgreSQL engine and explicit, versioned initial schema migration."""

from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.engine import Engine, make_url

from app.db.models.accounts import metadata, versions

SCHEMA_VERSION = 1


def database_engine(url: str) -> Engine:
    parsed = make_url(url)
    if parsed.drivername not in {"postgresql", "postgresql+psycopg"}:
        raise ValueError("DATABASE_URL must use postgresql+psycopg://")
    return create_engine(
        parsed.set(drivername="postgresql+psycopg"), pool_pre_ping=True,
        hide_parameters=True, connect_args={"connect_timeout": 5},
    )


def initialize_schema(engine: Engine) -> None:
    """Migration 1 is additive and transactional; it never drops existing data."""
    with engine.begin() as connection:
        connection.execute(text("SELECT pg_advisory_xact_lock(760019001)"))
        versions.create(connection, checkfirst=True)
        current = connection.execute(select(versions.c.version)).scalars().all()
        if current == [SCHEMA_VERSION]:
            return
        if current:
            raise RuntimeError("Unsupported account schema version; upgrade the application.")
        metadata.create_all(connection)
        connection.execute(versions.insert().values(version=SCHEMA_VERSION))


def check_schema(engine: Engine) -> None:
    with engine.connect() as connection:
        if not inspect(connection).has_table(versions.name):
            raise RuntimeError("Account tables are missing. Run: python -m app.db.manage init")
        if connection.execute(select(versions.c.version)).scalars().all() != [SCHEMA_VERSION]:
            raise RuntimeError("Unsupported account schema version; run the matching migration.")

