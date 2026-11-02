import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

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


def test_default_demo_account_is_seeded_once(setup):
    client, path = setup
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


def test_demo_seed_can_be_disabled(tmp_path, monkeypatch):
    monkeypatch.setenv("OWL_SEED_DEMO_ACCOUNT", "false")
    path = tmp_path / "accounts.json"
    client = TestClient(create_app(path))
    assert (
        client.post(
            "/api/v1/auth/login", json={"username": "admin", "password": "admin"}
        ).status_code
        == 401
    )
    assert not path.exists()
