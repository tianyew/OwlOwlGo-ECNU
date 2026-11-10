"""Real HTTP handlers, grading and atomic JSON persistence; no model calls."""

import json
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from tests.helpers import choose_topic, submit_quiz

QUIZ = "/api/v1/learning/units/travel/0/quiz"
SUBMIT = "/api/v1/learning/units/travel/0/submissions"
PROGRESS = "/api/v1/learning/progress"


@pytest.fixture
def unit(tmp_path):
    path = tmp_path / "accounts.json"
    settings = Settings(_env_file=None, deepseek_api_key="")
    app = create_app(path, settings)
    client = TestClient(app)
    client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin"})
    submit_quiz(client)
    choose_topic(client)
    return client, app, path, settings


def submission(client, answers=(0, 1)):
    quiz = client.get(QUIZ).json()
    return {
        "submission_id": str(uuid4()),
        "content_version": quiz["content_version"],
        "revision": client.get(PROGRESS).json()["revision"],
        "answers": [
            {"question_id": question["id"], "selected_index": answer}
            for question, answer in zip(quiz["questions"], answers, strict=True)
        ],
    }


def test_grade_complete_restart_and_keep_pass_on_failed_review(unit):
    client, _, path, settings = unit
    quiz = client.get(QUIZ).json()
    assert quiz["result"] is None
    assert all("answer" not in q and "explanation" not in q for q in quiz["questions"])
    wrong = client.post(SUBMIT, json=submission(client, (2, 1)))
    assert wrong.status_code == 200
    assert wrong.json()["result"]["score"] == 50
    assert not wrong.json()["result"]["passed"]
    assert not client.get(QUIZ).json()["unit_completed"]
    passed = client.post(SUBMIT, json=submission(client)).json()
    assert passed["result"]["score"] == 100
    assert passed["progress"]["state"]["completed"]["travel"] == [0]
    assert passed["progress"]["state"]["checks"]["travel:0"]["submitted"]
    assert "unit_submissions" not in passed["progress"]
    review = client.post(SUBMIT, json=submission(client, (2, 2))).json()
    assert review["result"]["score"] == 0
    assert review["progress"]["state"]["completed"]["travel"] == [0]
    restarted = TestClient(create_app(path, settings))
    restarted.cookies.update(client.cookies)
    restored = restarted.get(QUIZ).json()
    assert restored["result"] == review["result"]
    assert restored["unit_completed"]
    saved = json.loads(path.with_name("learning.json").read_text())
    assert (
        sum(
            r["kind"] == "unit"
            for r in next(iter(saved["progress"].values()))["submissions"].values()
        )
        == 3
    )


def test_retry_is_idempotent_and_cannot_replace_answers(unit):
    client, _, _, _ = unit
    body = submission(client)
    first = client.post(SUBMIT, json=body).json()
    assert client.post(SUBMIT, json=body).json() == first
    changed = deepcopy(body)
    changed["answers"][0]["selected_index"] = 2
    assert client.post(SUBMIT, json=changed).status_code == 409
    assert client.get(PROGRESS).json()["revision"] == first["progress"]["revision"]


@pytest.mark.parametrize("invalid", ["missing", "duplicate", "unknown", "option", "score", "bool"])
def test_invalid_answers_do_not_change_progress(unit, invalid):
    client, _, _, _ = unit
    body = submission(client)
    if invalid == "missing":
        body["answers"].pop()
    elif invalid == "duplicate":
        body["answers"][1] = body["answers"][0]
    elif invalid == "unknown":
        body["answers"][0]["question_id"] = "another-unit"
    elif invalid == "option":
        body["answers"][0]["selected_index"] = 3
    elif invalid == "score":
        body["score"] = 100
    else:
        body["answers"][0]["selected_index"] = True
    before = client.get(PROGRESS).json()
    assert client.post(SUBMIT, json=body).status_code == 422
    assert client.get(PROGRESS).json() == before


def test_version_revision_origin_and_ownership(unit):
    client, app, _, _ = unit
    body = submission(client)
    assert client.post(SUBMIT, json={**body, "content_version": 2}).status_code == 409
    assert client.post(SUBMIT, json={**body, "revision": 0}).status_code == 409
    assert (
        client.post(SUBMIT, json=body, headers={"Origin": "https://other.test"}).status_code == 403
    )
    anonymous = TestClient(app)
    assert anonymous.get(QUIZ).status_code == 401
    assert anonymous.post(SUBMIT, json=body).status_code == 401
    assert client.post(SUBMIT, json=body).status_code == 200
    other = TestClient(app)
    other.post(
        "/api/v1/auth/register",
        json={"username": "other", "password": "test-password", "display_name": "Other"},
    )
    assert other.get(QUIZ).json()["result"] is None
    assert other.post(SUBMIT, json={**body, "revision": 0}).status_code == 422


def test_progress_snapshots_cannot_award_or_revoke_completion(unit):
    client, _, _, _ = unit
    saved = client.get(PROGRESS).json()
    forged = deepcopy(saved["state"])
    forged["completed"] = {"travel": [0, 1]}
    forged["checks"] = {"travel:0": {"answers": [0, 1], "submitted": True}}
    response = client.put(PROGRESS, json={"revision": saved["revision"], "state": forged}).json()
    assert response["state"]["completed"]["travel"] == []
    assert "travel:0" not in response["state"]["checks"]
    assert client.post(SUBMIT, json=submission(client)).status_code == 200
    saved = client.get(PROGRESS).json()
    saved["state"]["completed"] = {}
    saved["state"]["checks"] = {}
    response = client.put(PROGRESS, json={"revision": saved["revision"], "state": saved["state"]})
    assert response.json()["state"]["completed"]["travel"] == [0]
    assert response.json()["state"]["checks"]["travel:0"]["answers"] == [0, 1]


def test_concurrent_retries_write_one_result(unit):
    client, app, _, _ = unit
    body = submission(client)
    user_id = client.get("/api/v1/auth/me").json()["id"]
    answers = {item["question_id"]: item["selected_index"] for item in body["answers"]}

    def submit(_):
        return app.state.learning.submit_unit(
            user_id, body["submission_id"], 1, answers, body["revision"]
        )["result"]

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(submit, range(8)))
    assert all(result == results[0] for result in results)
    record = app.state.learning.get(user_id)
    assert sum(r["kind"] == "unit" for r in record["submissions"].values()) == 1
    assert record["revision"] == body["revision"] + 1
