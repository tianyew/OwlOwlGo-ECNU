"""Exercise the public learning contract without fabricating official state."""

from uuid import uuid4

from app.domain.content.catalog import get_quiz


def login(client):
    """Create a real test account, or sign back into its persisted record."""
    credentials = {"username": "admin", "password": "test-password-42"}
    result = client.post(
        "/api/v1/auth/register", json={**credentials, "display_name": "测试账号"}
    )
    if result.status_code == 409:
        result = client.post("/api/v1/auth/login", json=credentials)
        assert result.status_code == 200, result.text
    else:
        assert result.status_code == 201, result.text


def submission_body(client, quiz_id, answers=None):
    questions = get_quiz(quiz_id)["questions"]
    if answers is None:
        answers = [q["answer"] for q in questions]
    return {
        "submission_id": str(uuid4()),
        "content_version": 1,
        "revision": client.get("/api/v1/learning/progress").json()["revision"],
        "answers": [
            {"question_id": q["id"], "selected_index": a}
            for q, a in zip(questions, answers, strict=True)
        ],
    }


def submit_quiz(client, quiz_id="assessment", answers=None):
    response = client.post(
        f"/api/v1/learning/quizzes/{quiz_id}/submissions",
        json=submission_body(client, quiz_id, answers),
    )
    assert response.status_code == 200, response.text
    return response.json()


def choose_topic(client, topic="travel"):
    saved = client.get("/api/v1/learning/progress").json()
    state = saved["state"]
    state.update(stage="plan", topic=topic)
    response = client.put(
        "/api/v1/learning/progress", json={"revision": saved["revision"], "state": state}
    )
    assert response.status_code == 200, response.text
    return response.json()
