"""Real PostgreSQL tests, isolated in a unique schema; never reset application tables."""

import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.schema import CreateSchema, DropSchema

from app.core.config import Settings
from app.core.security import hash_password, token_digest
from app.db.manage import cleanup, import_json
from app.db.models.accounts import attempts, sessions, users
from app.db.repositories.accounts import DuplicateUsername
from app.db.repositories.postgres_accounts import PostgresAccountRepository
from app.db.session import database_engine, initialize_schema
from app.main import create_app


@pytest.fixture
def database(tmp_path, pytestconfig):
    url = os.environ.get("OWL_TEST_DATABASE_URL")
    if not url and pytestconfig.getoption("--postgres"):
        url = Settings().database_url.get_secret_value()
        if not url:
            pytest.fail("--postgres requires DATABASE_URL in backend/.env")
    if not url:
        pytest.skip("Set OWL_TEST_DATABASE_URL to run real PostgreSQL integration tests")
    admin = database_engine(url)
    schema = f"test_auth_{uuid4().hex}"
    with admin.begin() as connection:
        connection.execute(CreateSchema(schema))
    scoped_url = admin.url.update_query_dict({"options": f"-csearch_path={schema}"})
    engine = database_engine(scoped_url)
    try:
        initialize_schema(engine)
        settings = Settings(
            _env_file=None, database_url=scoped_url.render_as_string(hide_password=False),
            owl_learning_file=tmp_path / "learning.json", owl_seed_demo_account=False,
            owl_login_account_limit=2, deepseek_api_key="",
        )
        yield engine, settings
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        admin.dispose()


ACCOUNT = {"username": "Alice_1", "password": "testing-pass-42", "display_name": "安娜"}


def test_real_postgres_registration_session_and_restart(database):
    engine, settings = database
    with TestClient(create_app(settings=settings)) as client:
        assert client.get("/api/v1/auth/me").status_code == 401
        registered = client.post("/api/v1/auth/register", json=ACCOUNT)
        assert registered.status_code == 201
        assert set(registered.json()) == {"id", "username", "display_name"}
        token = client.cookies.get("owl_session")
        with engine.connect() as connection:
            user = connection.execute(select(users)).mappings().one()
            session = connection.execute(select(sessions)).mappings().one()
            assert user["id"] == registered.json()["id"]
            assert user["username"] == "alice_1"
            assert user["password_hash"].startswith("scrypt$")
            assert ACCOUNT["password"] not in user["password_hash"]
            assert session["token_hash"] == token_digest(token)
        assert client.post("/api/v1/auth/register", json=ACCOUNT).status_code == 409
        assert client.get("/api/v1/learning/progress").status_code == 200
    with TestClient(create_app(settings=settings)) as restarted:
        restarted.cookies.set("owl_session", token)
        assert restarted.get("/api/v1/auth/me").json()["id"] == registered.json()["id"]
        assert restarted.post("/api/v1/auth/login", json={
            "username": " ALICE_1 ", "password": ACCOUNT["password"],
        }).status_code == 200
        assert PostgresAccountRepository(engine).session_user(token_digest(token), 0) is None
        assert restarted.post("/api/v1/auth/logout").status_code == 204
        assert restarted.get("/api/v1/auth/me").status_code == 401
        assert restarted.get("/api/v1/learning/progress").status_code == 401
    with engine.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(users)) == 1
        assert connection.scalar(select(func.count()).select_from(sessions)) == 0


def test_postgres_throttles_across_app_instances(database):
    engine, settings = database
    credentials = {"username": "unknown", "password": "bad-password"}
    with TestClient(create_app(settings=settings)) as first:
        for _ in range(2):
            assert first.post("/api/v1/auth/login", json=credentials).status_code == 401
    with TestClient(create_app(settings=settings)) as second:
        response = second.post("/api/v1/auth/login", json=credentials)
        assert response.status_code == 429
        assert int(response.headers["retry-after"]) > 0
    with engine.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(attempts)) == 2


def legacy_user(username="legacy"):
    return {
        "_id": str(uuid4()), "username": username, "display_name": "旧账号",
        "password_hash": hash_password("legacy-password"),
        "created_at": datetime.now(UTC).isoformat(), "schema_version": 1,
    }


def test_concurrent_unique_users_and_counter_reservations(database):
    engine, _ = database
    user = legacy_user()

    def register(_):
        try:
            PostgresAccountRepository(engine).create_user({**user, "_id": str(uuid4())})
            return True
        except DuplicateUsername:
            return False

    def attempt(_):
        return PostgresAccountRepository(engine).consume_auth_attempt({"a": 3, "b": 5}, 100, 60)

    with ThreadPoolExecutor(max_workers=6) as pool:
        assert sum(pool.map(register, range(12))) == 1
        results = list(pool.map(attempt, range(12)))
        assert results.count(0) == 3
        assert results.count(60) == 9
    repo = PostgresAccountRepository(engine)
    assert repo.consume_auth_attempt({"a": 3, "b": 5}, 160, 60) == 0
    cleanup(engine, 220)
    with engine.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(attempts)) == 0


def test_import_is_atomic_repeatable_and_preserves_identity(database, tmp_path):
    engine, settings = database
    path = tmp_path / "legacy.json"
    user = legacy_user()
    data = {"schema_version": 1, "users": [user], "sessions": [{"_id": "old-token"}]}
    original = json.dumps(data)
    path.write_text(original)
    assert import_json(engine, path, dry_run=True) == (1, 0)
    assert PostgresAccountRepository(engine).find_user("legacy") is None
    assert import_json(engine, path) == (1, 0)
    assert import_json(engine, path) == (0, 1)
    assert path.read_text() == original
    initialize_schema(engine)  # Re-running the migration preserves all records.
    with TestClient(create_app(settings=settings)) as client:
        response = client.post("/api/v1/auth/login", json={
            "username": "legacy", "password": "legacy-password",
        })
        assert response.status_code == 200
        assert response.json()["id"] == user["_id"]
    data["users"] = [legacy_user("newuser"), {**user, "display_name": "冲突"}]
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="conflict"):
        import_json(engine, path)
    assert PostgresAccountRepository(engine).find_user("newuser") is None
    assert PostgresAccountRepository(engine).find_user("legacy")["display_name"] == "旧账号"


def test_session_expiry_foreign_key_and_transaction_rollback(database):
    engine, _ = database
    repo = PostgresAccountRepository(engine)
    user = legacy_user()
    repo.create_user(user)
    session = {"_id": "a" * 64, "user_id": user["_id"], "created_at": 100, "expires_at": 160}
    repo.save_session(session, 100)
    assert repo.session_user("a" * 64, 159)["_id"] == user["_id"]
    assert repo.session_user("a" * 64, 160) is None
    with pytest.raises(IntegrityError):
        repo.save_session({**session, "_id": "b" * 64, "user_id": str(uuid4())}, 110, "a" * 64)
    assert repo.session_user("a" * 64, 110) is not None
