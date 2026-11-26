"""Verify actual file output, rotation and request privacy."""

import logging

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import Settings
from app.core.logging import configure_logging
from app.main import create_app


@pytest.fixture
def log_settings(tmp_path):
    logger = logging.getLogger("app")
    handlers, level, propagate = logger.handlers[:], logger.level, logger.propagate
    for handler in handlers:
        logger.removeHandler(handler)
    settings = Settings(
        _env_file=None,
        database_url="",
        owl_seed_demo_account=False,
        owl_log_file=tmp_path / "logs" / "app.log",
    )
    yield settings
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()
    for handler in handlers:
        logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = propagate


def test_file_logging_is_utf8_and_idempotent(log_settings):
    configure_logging(log_settings)
    configure_logging(log_settings)
    logger = logging.getLogger("app.tests")
    logger.debug("hidden_debug_event")
    logger.info("日志写入成功")
    contents = log_settings.owl_log_file.read_text(encoding="utf-8")
    assert contents.count("日志写入成功") == 1
    assert "INFO app.tests" in contents
    assert "hidden_debug_event" not in contents

    log_settings.owl_log_level = "DEBUG"
    configure_logging(log_settings)
    logger.debug("visible_debug_event")
    assert "visible_debug_event" in log_settings.owl_log_file.read_text(encoding="utf-8")


def test_file_rotation_is_bounded(log_settings):
    log_settings.owl_log_max_bytes = 150
    log_settings.owl_log_backup_count = 2
    configure_logging(log_settings)
    for index in range(20):
        logging.getLogger("app.tests").info("rotation_event_%02d", index)
    assert {p.name for p in log_settings.owl_log_file.parent.iterdir()} == {
        "app.log", "app.log.1", "app.log.2",
    }
    assert "rotation_event_19" in log_settings.owl_log_file.read_text(encoding="utf-8")


def test_changing_file_closes_previous_handler(log_settings):
    configure_logging(log_settings)
    logger = logging.getLogger("app.tests")
    logger.info("first_file_event")
    previous = log_settings.owl_log_file
    log_settings.owl_log_file = previous.with_name("other.log")
    configure_logging(log_settings)
    logger.info("second_file_event")
    assert "second_file_event" not in previous.read_text(encoding="utf-8")
    assert "second_file_event" in log_settings.owl_log_file.read_text(encoding="utf-8")


def test_requests_and_errors_do_not_log_submitted_secrets(log_settings, tmp_path):
    application = create_app(data_path=tmp_path / "accounts.json", settings=log_settings)
    secret = "private-value-92751"

    @application.get("/test/items/{item_id}")
    async def item(item_id: str):
        return {"ok": True}

    @application.get("/test/database")
    async def database_failure():
        raise SQLAlchemyError(secret)

    @application.get("/test/error")
    async def unexpected_failure():
        raise RuntimeError(secret)

    with TestClient(application, raise_server_exceptions=False) as client:
        assert client.get(
            f"/test/items/{secret}?token={secret}",
            headers={"Authorization": f"Bearer {secret}", "Cookie": f"session={secret}"},
        ).status_code == 200
        assert client.get(f"/missing/{secret}").status_code == 404
        invalid = client.post("/api/v1/auth/login", json={"password": secret})
        assert invalid.status_code == 422
        assert invalid.headers["Cache-Control"] == "no-store"
        assert client.get("/test/database").status_code == 503
        assert client.get("/test/error").status_code == 500

    contents = log_settings.owl_log_file.read_text(encoding="utf-8")
    assert secret not in contents
    assert "route=/test/items/{item_id} status=200 duration_ms=" in contents
    assert "route=<unmatched> status=404" in contents
    assert "status=422" in contents
    assert "status=503" in contents
    assert "status=500" in contents
    assert "SQLAlchemyError" in contents
    assert "RuntimeError" in contents
    assert "application_started" in contents
    assert "application_stopped" in contents
