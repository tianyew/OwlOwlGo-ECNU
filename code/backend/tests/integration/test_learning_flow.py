"""Full curriculum, authority, migrations and evidence coverage over real handlers."""

import json
from copy import deepcopy
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.domain.content.catalog import QUIZZES, TOPIC_IDS, get_quiz, grade
from app.main import create_app
from app.schemas.learning import KEY, LearningState
from tests.helpers import choose_topic, login, submission_body, submit_quiz

PROGRESS = "/api/v1/learning/progress"


@pytest.fixture
def flow(tmp_path):
    path = tmp_path / "accounts.json"
    settings = Settings(_env_file=None, deepseek_api_key="")
    app = create_app(path, settings)
    client = TestClient(app)
    login(client)
    return client, app, path, settings


def test_entire_curriculum_uses_server_grading_and_produces_a_real_matrix(flow):
    client, _, _, _ = flow
    catalog = client.get("/api/v1/learning/curriculum")
    assert catalog.status_code == 200
    assert len(catalog.json()["topics"]) == 4
    for topic in catalog.json()["topics"]:
        assert len(topic["units"]) == 5
        assert "posttest" not in topic
        assert all("quiz" not in unit for unit in topic["units"])
    submit_quiz(client)
    for topic in TOPIC_IDS:
        choose_topic(client, topic)
        for index in range(5):
            quiz_id = f"unit-{topic}-{index}"
            quiz = client.get(f"/api/v1/learning/quizzes/{quiz_id}").json()
            assert len(quiz["questions"]) == 2
            assert all("answer" not in q and "explanation" not in q for q in quiz["questions"])
            response = submit_quiz(client, quiz_id)
            assert response["result"]["score"] == 100
            assert response["progress"]["state"]["completed"][topic] == list(range(index + 1))
        response = submit_quiz(client, f"post-{topic}")
        assert response["result"]["total"] == 10
        assert response["progress"]["topic_completion"][topic]
    saved = client.get(PROGRESS).json()
    assert all(saved["topic_completion"].values())
    profile = saved["profile"]
    assert profile["submission_count"] == 25
    assert profile["attempt_count"] == 88
    assert profile["evidence_count"] == 68
    assert profile["repeat_count"] == 20
    assert profile["score"] == 100
    assert len(profile["matrix"]) == 7
    assert all(len(row["cells"]) == 6 for row in profile["matrix"])
    for row in profile["matrix"]:
        if row["dimension"] in {"reading", "information", "classical", "writing"}:
            assert row["score"] is None
            assert row["evidence_count"] == 0
            assert all(cell["score"] is None for cell in row["cells"])
    assert client.get("/api/v1/learning/profile").json() == profile


def test_progress_cannot_forge_pretest_or_learning_evidence(flow):
    client, _, _, _ = flow
    forged = LearningState().model_dump()
    forged.update(
        stage="plan",
        topic="travel",
        onboarding_complete=True,
        quiz={
            "stage": "result",
            "current": 7,
            "selected": KEY[-1],
            "submitted": True,
            "answers": KEY,
        },
        completed={topic: [0, 1, 2, 3, 4] for topic in TOPIC_IDS},
        checks={"travel:0": {"answers": [0, 1], "submitted": True}},
        posttests={"travel": {"answers": [0] * 10, "submitted": True}},
    )
    response = client.put(PROGRESS, json={"revision": 0, "state": forged})
    assert response.status_code == 200
    saved = response.json()
    assert saved["results"] == {}
    assert saved["profile"]["evidence_count"] == 0
    assert saved["state"]["quiz"]["stage"] == "intro"
    assert saved["state"]["topic"] is None
    assert all(not units for units in saved["state"]["completed"].values())
    assert saved["state"]["checks"] == saved["state"]["posttests"] == {}
    assert client.post("/api/v1/learning/analysis").status_code == 400
    assert (
        client.post(
            "/api/v1/learning/quizzes/unit-travel-0/submissions",
            json=submission_body(client, "unit-travel-0"),
        ).status_code
        == 422
    )


def test_repeated_questions_update_practice_without_inflating_first_evidence(flow):
    client, _, _, _ = flow
    submit_quiz(client)
    choose_topic(client)
    wrong = submit_quiz(client, "unit-travel-0", answers=[2, 2])["progress"]
    assert wrong["profile"]["evidence_count"] == 10
    assert wrong["profile"]["score"] == 80
    right = submit_quiz(client, "unit-travel-0")["progress"]
    assert right["profile"]["evidence_count"] == 10
    assert right["profile"]["score"] == 80
    assert right["profile"]["latest_score"] == 100
    assert right["profile"]["repeat_count"] == 2
    assert right["state"]["completed"]["travel"] == [0]
    post = submit_quiz(client, "post-travel")["progress"]
    assert post["profile"]["evidence_count"] == 19
    assert post["profile"]["repeat_count"] == 3
    assert not post["topic_completion"]["travel"]


def test_retries_and_cross_quiz_uuid_reuse_do_not_create_evidence(flow):
    client, _, _, _ = flow
    body = submission_body(client, "assessment")
    url = "/api/v1/learning/quizzes/assessment/submissions"
    first = client.post(url, json=body)
    assert first.status_code == 200
    assert client.post(url, json=body).json() == first.json()
    before = client.get(PROGRESS).json()
    duplicate = submission_body(client, "assessment")
    assert client.post(url, json=duplicate).status_code == 422
    assert client.get(PROGRESS).json() == before
    choose_topic(client)
    reused = submission_body(client, "unit-travel-0")
    reused["submission_id"] = body["submission_id"]
    assert (
        client.post("/api/v1/learning/quizzes/unit-travel-0/submissions", json=reused).status_code
        == 409
    )


def test_reset_requires_a_new_pretest_but_keeps_unit_passes_and_profile(flow):
    client, _, _, _ = flow
    body = submission_body(client, "assessment")
    first = client.post("/api/v1/learning/quizzes/assessment/submissions", json=body).json()
    assert first["result"]["score"] == 100
    choose_topic(client)
    submit_quiz(client, "unit-travel-0")
    previous = client.get(PROGRESS).json()
    response = client.post(
        "/api/v1/learning/assessment/reset", json={"revision": previous["revision"]}
    )
    assert response.status_code == 200
    reset = response.json()
    assert "assessment" not in reset["results"]
    assert reset["state"]["topic"] is None
    assert reset["state"]["completed"]["travel"] == [0]
    assert reset["profile"] == previous["profile"]
    assert (
        client.post("/api/v1/learning/quizzes/assessment/submissions", json=body).status_code == 409
    )
    next_result = submit_quiz(client, answers=[1, *KEY[1:]])
    assert next_result["result"]["score"] == 88
    assert next_result["progress"]["profile"]["evidence_count"] == 10
    assert next_result["progress"]["profile"]["repeat_count"] == 8


def test_saved_draft_is_not_a_submission_and_restores_after_restart(flow):
    client, _, path, settings = flow
    state = client.get(PROGRESS).json()["state"]
    state["drafts"]["assessment"] = {
        "content_version": 1,
        "current": 3,
        "answers": [{"question_id": "initial", "selected_index": 0}],
    }
    assert client.put(PROGRESS, json={"revision": 0, "state": state}).status_code == 200
    restarted = TestClient(create_app(path, settings))
    restarted.cookies.update(client.cookies)
    quiz = restarted.get("/api/v1/learning/quizzes/assessment").json()
    assert quiz["draft"]["current"] == 3 and len(quiz["draft"]["answers"]) == 1
    assert quiz["result"] is None
    assert restarted.get(PROGRESS).json()["profile"]["evidence_count"] == 0
    for change in ("question", "duplicate", "page"):
        invalid = deepcopy(state)
        draft = invalid["drafts"]["assessment"]
        if change == "question":
            draft["answers"][0]["question_id"] = "travel-0-expression"
        elif change == "duplicate":
            draft["answers"] *= 2
        else:
            draft["current"] = 8
        assert client.put(PROGRESS, json={"revision": 1, "state": invalid}).status_code == 422


def test_progress_snapshot_cannot_revoke_grades_or_profile(flow):
    client, _, _, _ = flow
    submit_quiz(client)
    choose_topic(client, "poetry")
    submit_quiz(client, "unit-poetry-4")
    before = submit_quiz(client, "post-poetry")["progress"]
    state = LearningState().model_dump()
    response = client.put(PROGRESS, json={"revision": before["revision"], "state": state}).json()
    assert response["results"] == before["results"]
    assert response["profile"] == before["profile"]
    assert response["state"]["completed"]["poetry"] == [4]
    assert response["state"]["posttests"]["poetry"]["submitted"]


def test_completed_direction_stays_complete_after_a_failed_review(flow):
    client, _, _, _ = flow
    submit_quiz(client)
    choose_topic(client, "campus")
    for index in range(5):
        submit_quiz(client, f"unit-campus-{index}")
    before_post = client.get(PROGRESS).json()
    assert not before_post["topic_completion"]["campus"]
    submit_quiz(client, "post-campus")
    questions = get_quiz("post-campus")["questions"]
    wrong = [(q["answer"] + 1) % len(q["options"]) for q in questions]
    response = submit_quiz(client, "post-campus", answers=wrong)
    assert response["result"]["score"] == 0
    assert response["progress"]["topic_completion"]["campus"]


def test_legacy_pilot_pass_migrates_but_other_client_completion_is_archived(flow):
    client, app, _, _ = flow
    user_id = client.get("/api/v1/auth/me").json()["id"]
    state = LearningState().model_dump()
    state.update(
        stage="plan",
        topic="travel",
        onboarding_complete=True,
        quiz={
            "stage": "result",
            "current": 7,
            "selected": KEY[-1],
            "submitted": True,
            "answers": KEY,
        },
        completed={"travel": [0, 1, 2]},
    )
    pilot_id = str(uuid4())
    pilot = grade(
        "unit-travel-0", {q["id"]: q["answer"] for q in get_quiz("unit-travel-0")["questions"]}
    )
    pilot["created_at"] = "2026-11-09T00:00:00Z"
    legacy = {
        "schema_version": 1,
        "progress": {
            user_id: {
                "revision": 7,
                "state": state,
                "updated_at": pilot["created_at"],
                "analysis": None,
                "unit_submissions": {pilot_id: pilot},
            }
        },
    }
    app.state.learning.path.write_text(json.dumps(legacy))
    saved = client.get(PROGRESS).json()
    assert saved["state"]["completed"]["travel"] == [0]
    assert saved["results"]["assessment"]["score"] == 100
    assert saved["profile"]["evidence_count"] == 2
    assert saved["profile"]["submission_count"] == 1
    assert "legacy_progress" not in saved
    assert client.put(PROGRESS, json={"revision": 7, "state": saved["state"]}).status_code == 200
    record = json.loads(app.state.learning.path.read_text())["progress"][user_id]
    assert record["legacy_progress"]["completed"]["travel"] == [0, 1, 2]
    assert record["authority_version"] == 2 and len(record["submissions"]) == 2
    assert client.get(PROGRESS).json()["profile"] == saved["profile"]


def test_public_content_contains_no_personal_results_and_profile_is_isolated(flow):
    client, app, _, _ = flow
    submit_quiz(client)
    anonymous = TestClient(app)
    assert anonymous.get("/api/v1/learning/curriculum").status_code == 200
    quiz = anonymous.get("/api/v1/learning/quizzes/assessment").json()
    assert quiz["result"] is None and quiz["draft"] is None
    assert anonymous.get("/api/v1/learning/profile").status_code == 401
    other = TestClient(app)
    other.post(
        "/api/v1/auth/register",
        json={"username": "other", "password": "testing-password", "display_name": "Other"},
    )
    assert other.get("/api/v1/learning/profile").json()["evidence_count"] == 0
    assert other.get("/api/v1/learning/quizzes/assessment").json()["result"] is None
    assert client.get("/api/v1/learning/quizzes/unknown").status_code == 404
    assert client.get("/api/v1/learning/units/travel/9/quiz").status_code == 404


def test_every_question_has_stable_evidence_tags_and_valid_answers():
    assert len(QUIZZES) == 25
    for quiz in QUIZZES.values():
        ids = [q["id"] for q in quiz["questions"]]
        assert len(ids) == len(set(ids))
        for question in quiz["questions"]:
            assert 0 <= question["answer"] < len(question["options"])
            assert question["source_question_id"]
            assert question["dimension"] in {"phonetics", "vocabulary", "poetry"}
            assert question["bloom"] in {"remember", "understand", "apply"}


def test_legacy_partial_pretest_is_migrated_as_a_draft_without_awarding_evidence(flow):
    client, app, _, _ = flow
    user_id = client.get("/api/v1/auth/me").json()["id"]
    state = LearningState().model_dump()
    state["quiz"] = {
        "stage": "quiz",
        "current": 1,
        "selected": 2,
        "submitted": False,
        "answers": [0],
    }
    old = {"revision": 3, "state": state, "analysis": None, "updated_at": None}
    app.state.learning.path.write_text(
        json.dumps({"schema_version": 1, "progress": {user_id: old}})
    )
    saved = client.get(PROGRESS).json()
    assert saved["state"]["drafts"]["assessment"] == {
        "content_version": 1,
        "current": 1,
        "answers": [
            {"question_id": "initial", "selected_index": 0},
            {"question_id": "final", "selected_index": 2},
        ],
    }
    assert saved["profile"]["evidence_count"] == 0
    assert saved["results"] == {}


@pytest.mark.parametrize("correct,passed", [(0, False), (5, False), (6, True), (10, True)])
def test_posttest_pass_threshold_is_sixty_without_requiring_unit_completion(flow, correct, passed):
    client, _, _, _ = flow
    submit_quiz(client)
    choose_topic(client, "daily")
    questions = get_quiz("post-daily")["questions"]
    answers = [
        q["answer"] if i < correct else (q["answer"] + 1) % len(q["options"])
        for i, q in enumerate(questions)
    ]
    response = submit_quiz(client, "post-daily", answers=answers)
    assert response["result"]["score"] == correct * 10
    assert response["result"]["passed"] is passed
    assert not response["progress"]["topic_completion"]["daily"]


def test_zero_score_pretest_still_allows_topic_selection(flow):
    client, _, _, _ = flow
    questions = get_quiz("assessment")["questions"]
    answers = [(q["answer"] + 1) % len(q["options"]) for q in questions]
    response = submit_quiz(client, answers=answers)
    assert response["result"]["score"] == 0
    saved = choose_topic(client)
    assert saved["state"]["topic"] == "travel"
    assert saved["profile"]["score"] == 0
