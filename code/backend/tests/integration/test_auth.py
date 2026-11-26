import json
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.security import token_digest
from app.db.repositories.accounts import DuplicateUsername, JsonAccountRepository
from app.main import create_app


@pytest.fixture
def setup(tmp_path):
    path = tmp_path / "accounts.json"
    return TestClient(create_app(path)), path


ACCOUNT = {"username": "Alice_1", "password": "testing-pass-42", "display_name": "安娜"}


def test_registration_persistence_login_logout(setup):
    client, path = setup
    assert client.get("/api/v1/auth/me").status_code == 401
    result = client.post("/api/v1/auth/register", json=ACCOUNT)
    assert result.status_code == 201
    assert result.json()["username"] == "alice_1"
    assert set(result.json()) == {"id", "username", "display_name"}
    cookie = result.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=strict" in cookie
    token = client.cookies.get("owl_session")
    content = path.read_text()
    assert ACCOUNT["password"] not in content and token not in content
    assert "scrypt$" in content
    assert client.get("/api/v1/auth/me").json()["display_name"] == "安娜"
    assert client.get("/api/v1/auth/me").headers["cache-control"] == "no-store"
    restarted = TestClient(create_app(path))
    restarted.cookies.set("owl_session", token)
    assert restarted.get("/api/v1/auth/me").status_code == 200
    assert client.post("/api/v1/auth/logout").status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401
    assert restarted.get("/api/v1/auth/me").status_code == 401
    logged_in = client.post(
        "/api/v1/auth/login", json={"username": " ALICE_1 ", "password": ACCOUNT["password"]}
    )
    assert logged_in.status_code == 200
    assert logged_in.json()["id"] == result.json()["id"]
    assert client.cookies.get("owl_session") != token


def test_invalid_duplicate_and_cross_origin_requests(setup):
    client, _ = setup
    assert client.post("/api/v1/auth/register", json=ACCOUNT).status_code == 201
    assert client.post("/api/v1/auth/register", json=ACCOUNT).status_code == 409
    for username in ("Alice_1", "absent"):
        result = client.post(
            "/api/v1/auth/login", json={"username": username, "password": "wrong-password"}
        )
        assert result.status_code == 401
        assert result.json()["detail"] == "账号或密码不正确。"
    result = client.post("/api/v1/auth/register", json={**ACCOUNT, "password": "short"})
    assert result.status_code == 422
    assert "short" not in result.text
    assert (
        client.post("/api/v1/auth/register", json={**ACCOUNT, "display_name": "  "}).status_code
        == 422
    )
    for endpoint in ("register", "login", "logout"):
        result = client.post(
            f"/api/v1/auth/{endpoint}", json=ACCOUNT, headers={"Origin": "https://other.example"}
        )
        assert result.status_code == 403


def test_expiration_and_session_rotation(setup):
    client, path = setup
    client.post("/api/v1/auth/register", json=ACCOUNT)
    first = client.cookies.get("owl_session")
    client.post("/api/v1/auth/login", json={k: ACCOUNT[k] for k in ("username", "password")})
    data = json.loads(path.read_text())
    assert token_digest(first) not in [s["_id"] for s in data["sessions"]]
    data["sessions"][0]["expires_at"] = 0
    path.write_text(json.dumps(data))
    assert client.get("/api/v1/auth/me").status_code == 401
    client.cookies.set("owl_session", "forged")
    assert client.get("/api/v1/auth/me").status_code == 401


def test_concurrent_registration_and_corruption(tmp_path):
    path = tmp_path / "accounts.json"

    def create(index):
        repo = JsonAccountRepository(path)
        try:
            repo.create_user({"_id": str(index), "username": "same"})
            return True
        except DuplicateUsername:
            return False

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(create, range(12)))
    assert sum(results) == 1
    assert len(json.loads(path.read_text())["users"]) == 1
    path.write_text("broken")
    with pytest.raises(json.JSONDecodeError):
        JsonAccountRepository(path).create_user({"_id": "new", "username": "new"})
    assert path.read_text() == "broken"


def test_secure_cookie_configuration(tmp_path, monkeypatch):
    monkeypatch.setenv("OWL_SECURE_COOKIES", "true")
    client = TestClient(create_app(tmp_path / "accounts.json"), base_url="https://testserver")
    result = client.post("/api/v1/auth/register", json=ACCOUNT)
    assert "Secure" in result.headers["set-cookie"]
    assert client.get("/api/v1/auth/me").status_code == 200


def test_demo_account_is_opt_in_and_seeded_once(tmp_path, monkeypatch):
    monkeypatch.setenv("OWL_SEED_DEMO_ACCOUNT", "true")
    path = tmp_path / "accounts.json"
    client = TestClient(create_app(path))
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin"})
    assert response.status_code == 200
    original = json.loads(path.read_text())["users"][0]
    TestClient(create_app(path))
    users = json.loads(path.read_text())["users"]
    assert len([u for u in users if u["username"] == "admin"]) == 1
    assert users[0] == original
    assert (
        client.post(
            "/api/v1/auth/register",
            json={"username": "shortpass", "password": "admin", "display_name": "Test"},
        ).status_code
        == 422
    )


def test_demo_seed_disabled_by_default(tmp_path):
    path = tmp_path / "accounts.json"
    client = TestClient(create_app(path, Settings(_env_file=None)))
    assert (
        client.post(
            "/api/v1/auth/login", json={"username": "admin", "password": "admin"}
        ).status_code
        == 401
    )
    assert json.loads(path.read_text())["users"] == []


def test_account_throttle_persists_and_expires(tmp_path, monkeypatch):
    now = 1000
    monkeypatch.setattr("app.api.v1.endpoints.auth.time", SimpleNamespace(time=lambda: now))
    settings = Settings(_env_file=None, owl_login_account_limit=2, owl_auth_window_seconds=60)
    path = tmp_path / "accounts.json"
    client = TestClient(create_app(path, settings))
    client.post("/api/v1/auth/register", json=ACCOUNT)
    wrong = {"username": " ALICE_1 ", "password": "incorrect"}
    for _ in range(2):
        assert client.post("/api/v1/auth/login", json=wrong).status_code == 401
    restarted = TestClient(create_app(path, settings), client=("another-ip", 5000))
    valid = {"username": "alice_1", "password": ACCOUNT["password"]}
    with patch("app.api.v1.endpoints.auth.verify_password") as verify:
        response = restarted.post("/api/v1/auth/login", json=valid)
        assert response.status_code == 429
        assert response.headers["retry-after"] == "60"
        verify.assert_not_called()
    now += 60
    assert restarted.post("/api/v1/auth/login", json=valid).status_code == 200


def test_ip_throttle_covers_unknown_users_and_registration(tmp_path):
    settings = Settings(_env_file=None, owl_login_ip_limit=2, owl_register_ip_limit=1)
    client = TestClient(create_app(tmp_path / "accounts.json", settings))
    for index in range(3):
        response = client.post(
            "/api/v1/auth/login", json={"username": f"absent{index}", "password": "bad"},
            headers={"X-Forwarded-For": f"203.0.113.{index}"},
        )
        assert response.status_code == (401 if index < 2 else 429)
    assert client.post("/api/v1/auth/register", json=ACCOUNT).status_code == 201
    assert client.post(
        "/api/v1/auth/register", json={**ACCOUNT, "username": "second"}
    ).status_code == 429
    # Throttling does not prevent reading or ending an existing session.
    assert client.get("/api/v1/auth/me").status_code == 200
    assert client.post("/api/v1/auth/logout").status_code == 204


def test_concurrent_attempts_share_the_limit(tmp_path):
    path = tmp_path / "accounts.json"

    def attempt(_):
        return JsonAccountRepository(path).consume_auth_attempt({"key": 3}, 100, 60)

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(attempt, range(12)))
    assert results.count(0) == 3
    assert results.count(60) == 9


@pytest.mark.parametrize("origin", [
    "https://testserver", "null", "http://testserver:81", "http://testserver/path",
    "http://testserver:invalid", "http://[", "http://user@testserver",
])
def test_origin_checks_scheme_port_and_malformed_values(setup, origin):
    client, _ = setup
    assert client.post(
        "/api/v1/auth/register", json=ACCOUNT, headers={"Origin": origin}
    ).status_code == 403


def test_same_origin_and_fetch_metadata(setup):
    client, _ = setup
    assert client.post(
        "/api/v1/auth/register", json=ACCOUNT, headers={"Origin": "http://testserver:80"}
    ).status_code == 201
    assert client.post(
        "/api/v1/auth/logout", headers={"Sec-Fetch-Site": "cross-site"}
    ).status_code == 403
    assert client.get("/api/v1/auth/me").status_code == 200


def test_auth_settings_load_from_env_file_and_environment(tmp_path, monkeypatch):
    path = tmp_path / "configured.json"
    env = tmp_path / ".env"
    env.write_text(
        f"OWL_ACCOUNT_FILE={path}\nOWL_SECURE_COOKIES=true\n"
        "OWL_SESSION_SECONDS=120\nOWL_SEED_DEMO_ACCOUNT=false\n"
    )
    settings = Settings(_env_file=env)
    client = TestClient(create_app(settings=settings), base_url="https://testserver")
    response = client.post("/api/v1/auth/register", json=ACCOUNT)
    assert response.status_code == 201
    assert "Secure" in response.headers["set-cookie"]
    assert "Max-Age=120" in response.headers["set-cookie"]
    session = json.loads(path.read_text())["sessions"][0]
    assert session["expires_at"] - session["created_at"] == 120
    monkeypatch.setenv("OWL_SESSION_SECONDS", "180")
    assert Settings(_env_file=env).owl_session_seconds == 180
