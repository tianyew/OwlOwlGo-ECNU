import json
from copy import deepcopy
from unittest.mock import Mock

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.integrations.llm.deepseek import AnalysisUnavailable, DeepSeekClient
from app.main import create_app
from app.schemas.learning import KEY, PROMPT_VERSION, LearningState, evidence, fingerprint
from app.services.agents.assessment import AnalysisContent, AssessmentAgent
from tests.helpers import choose_topic, submit_quiz


def login(client):
    assert (
        client.post(
            "/api/v1/auth/login", json={"username": "admin", "password": "admin"}
        ).status_code
        == 200
    )


def finished():
    return {
        **LearningState().model_dump(),
        "stage": "plan",
        "topic": "travel",
        "quiz": {
            "stage": "result",
            "current": 7,
            "selected": KEY[-1],
            "submitted": True,
            "answers": KEY,
        },
        "completed": {"travel": [0]},
    }


@pytest.fixture
def setup(tmp_path):
    path = tmp_path / "accounts.json"
    settings = Settings(_env_file=None, deepseek_api_key="")
    app = create_app(path, settings=settings)
    client = TestClient(app)
    login(client)
    return client, app, path, settings


def test_roundtrip_partial_plan_and_isolation(setup):
    client, app, path, settings = setup
    state = LearningState().model_dump()
    state["drafts"] = {
        "assessment": {
            "content_version": 1,
            "current": 0,
            "answers": [{"question_id": "initial", "selected_index": 2}],
        }
    }
    saved = client.put("/api/v1/learning/progress", json={"revision": 0, "state": state})
    assert saved.status_code == 200
    restarted = TestClient(create_app(path, settings=settings))
    login(restarted)
    assert restarted.get("/api/v1/learning/progress").json()["state"] == saved.json()["state"]
    submit_quiz(restarted)
    choose_topic(restarted)
    assert restarted.get("/api/v1/learning/progress").json()["state"]["completed"]["travel"] == []
    other = TestClient(app)
    other.post(
        "/api/v1/auth/register",
        json={"username": "other", "display_name": "Other", "password": "test-password"},
    )
    assert other.get("/api/v1/learning/progress").json()["revision"] == 0
    assert other.post("/api/v1/learning/analysis").status_code == 400
    anonymous = TestClient(app)
    assert anonymous.get("/api/v1/learning/progress").status_code == 401
    assert (
        anonymous.put("/api/v1/learning/progress", json={"revision": 0, "state": state}).status_code
        == 401
    )
    assert anonymous.post("/api/v1/learning/analysis").status_code == 401


def test_validation_conflict_and_origin(setup):
    client, _, _, _ = setup
    state = finished()
    assert (
        client.put("/api/v1/learning/progress", json={"revision": 0, "state": state}).status_code
        == 200
    )
    assert (
        client.put("/api/v1/learning/progress", json={"revision": 0, "state": state}).status_code
        == 409
    )
    assert (
        client.put(
            "/api/v1/learning/progress",
            json={"revision": 1, "state": state},
            headers={"Origin": "https://other.example"},
        ).status_code
        == 403
    )
    for field, value in [
        ("topic", "unknown"),
        ("completed", {"travel": [9]}),
        ("user_id", "other"),
    ]:
        invalid = {**state, field: value}
        assert (
            client.put(
                "/api/v1/learning/progress", json={"revision": 1, "state": invalid}
            ).status_code
            == 422
        )
    invalid = deepcopy(state)
    invalid["quiz"]["answers"] = [0]
    assert (
        client.put("/api/v1/learning/progress", json={"revision": 1, "state": invalid}).status_code
        == 422
    )


def test_analysis_missing_key_cache_and_invalidation(setup):
    client, app, _, _ = setup
    submit_quiz(client)
    result = client.post("/api/v1/learning/analysis")
    assert result.status_code == 503 and "学习建议暂不可用" in result.json()["detail"]
    fake = Mock(
        return_value={"summary": "test", "provider": "deepseek", "prompt_version": PROMPT_VERSION}
    )
    app.state.agents.agents["assessment_review"].analyze = fake
    result = client.post("/api/v1/learning/analysis")
    assert result.status_code == 200
    assert fake.call_args.args[0]["correct"] == 8
    assert "admin" not in json.dumps(fake.call_args.args[0])
    assert client.post("/api/v1/learning/analysis").json() == result.json()
    assert fake.call_count == 1
    choose_topic(client)
    submit_quiz(client, "unit-travel-0")
    assert client.get("/api/v1/learning/progress").json()["analysis"] == result.json()
    client.post("/api/v1/learning/analysis")
    assert fake.call_count == 1
    revision = client.get("/api/v1/learning/progress").json()["revision"]
    assert (
        client.post("/api/v1/learning/assessment/reset", json={"revision": revision}).status_code
        == 200
    )
    submit_quiz(client, answers=[1, *KEY[1:]])
    assert client.get("/api/v1/learning/progress").json()["analysis"] is None
    client.post("/api/v1/learning/analysis")
    assert fake.call_count == 2


@pytest.mark.parametrize("same_answers", [False, True])
def test_stale_analysis_does_not_overwrite_new_progress(setup, same_answers):
    client, app, _, _ = setup
    submit_quiz(client)

    def analyze(_):
        revision = client.get("/api/v1/learning/progress").json()["revision"]
        client.post("/api/v1/learning/assessment/reset", json={"revision": revision})
        submit_quiz(client, answers=KEY if same_answers else [1, *KEY[1:]])
        return {"summary": "stale"}

    app.state.agents.agents["assessment_review"].analyze = analyze
    assert client.post("/api/v1/learning/analysis").status_code == 409
    assert client.get("/api/v1/learning/progress").json()["analysis"] is None


@pytest.mark.parametrize(
    "mode", ["valid", "empty", "truncated", "invalid", "unauthorized", "timeout"]
)
def test_deepseek_transport_and_output_validation(monkeypatch, mode):
    settings = Settings(_env_file=None, deepseek_api_key="test-only-key")
    real_client = httpx.Client

    def handler(request):
        body = json.loads(request.content)
        assert request.url == "https://api.deepseek.com/chat/completions"
        assert body["response_format"] == {"type": "json_object"}
        assert body["max_tokens"] == 4000
        assert request.headers["Authorization"] == "Bearer test-only-key"
        if mode == "timeout":
            raise httpx.ReadTimeout("secret upstream data")
        if mode == "unauthorized":
            return httpx.Response(401, text="test-only-key")
        content = json.dumps(
            {
                "summary": "范围有限",
                "strengths": ["拼音"],
                "focus_areas": [],
                "question_feedback": [],
                "practice_tasks": [
                    {
                        "title": "练习",
                        "reason": "迁移",
                        "question_ids": ["initial"],
                        "activity": "拆分拼音",
                        "success_criterion": "核对声母",
                    }
                ]
                * 2,
                "next_steps": ["复习例句", "迁移练习"],
            }
        )
        if mode == "empty":
            content = " "
        if mode == "invalid":
            content = '{"score": 100}'
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "length" if mode == "truncated" else "stop",
                        "message": {"content": content},
                    }
                ]
            },
        )

    monkeypatch.setattr(
        "app.integrations.llm.deepseek.httpx.Client",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs),
    )
    if mode == "valid":
        assert (
            AssessmentAgent(DeepSeekClient(settings)).analyze(evidence(finished()))["provider"]
            == "deepseek"
        )
    else:
        with pytest.raises(AnalysisUnavailable) as error:
            AssessmentAgent(DeepSeekClient(settings)).analyze(evidence(finished()))
        assert "test-only-key" not in str(error.value)
        assert "secret" not in str(error.value)


def test_config_file_and_environment_override(tmp_path, monkeypatch):
    config = tmp_path / ".env"
    config.write_text("DEEPSEEK_API_KEY=file-only-key\nDEEPSEEK_MODEL=file-model\n")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    assert Settings(_env_file=config).deepseek_api_key.get_secret_value() == "file-only-key"
    monkeypatch.setenv("DEEPSEEK_API_KEY", "env-only-key")
    settings = Settings(_env_file=config)
    assert settings.deepseek_api_key.get_secret_value() == "env-only-key"
    assert "env-only-key" not in repr(settings)


def test_setup_completion_validation_and_legacy_migration(setup):
    client, app, _, _ = setup
    incomplete = LearningState().model_dump()
    incomplete["onboarding_complete"] = True
    assert (
        client.put(
            "/api/v1/learning/progress", json={"revision": 0, "state": incomplete}
        ).status_code
        == 422
    )
    submit_quiz(client)
    saved = choose_topic(client)
    state = saved["state"]
    state["onboarding_complete"] = True
    assert (
        client.put(
            "/api/v1/learning/progress", json={"revision": saved["revision"], "state": state}
        ).status_code
        == 200
    )
    assert client.get("/api/v1/learning/progress").json()["state"]["onboarding_complete"]
    # A pre-Home stored plan has no completion flag; preserve it as an existing learner.
    path = app.state.learning.path
    data = json.loads(path.read_text())
    for record in data["progress"].values():
        del record["state"]["onboarding_complete"]
    path.write_text(json.dumps(data))
    assert client.get("/api/v1/learning/progress").json()["state"]["onboarding_complete"]


def test_per_question_evidence_changes_cache_even_at_same_score():
    first = deepcopy(finished())
    second = deepcopy(finished())
    first["quiz"]["answers"][0] = 1
    second["quiz"]["answers"][1] = 1
    assert evidence(first)["score"] == evidence(second)["score"]
    assert evidence(first)["dimensions"] == evidence(second)["dimensions"]
    assert fingerprint(first) != fingerprint(second)
    item = evidence(first)["items"][0]
    assert item["selected_answer"] == "a"
    assert item["correct_answer"] == "m"
    assert not item["is_correct"]
    assert item["explanation"]


def test_analysis_requires_grounded_wrong_answer_feedback():
    state = deepcopy(finished())
    state["quiz"]["answers"][0] = 1
    data = {
        "summary": "本题可能混淆声母和韵母",
        "strengths": [],
        "focus_areas": ["声母"],
        "next_steps": ["辨认", "应用"],
        "question_feedback": [
            {"question_id": "initial", "observation": "选了a而不是m", "suggestion": "拆分ma"}
        ],
        "practice_tasks": [
            {
                "title": "拆分",
                "reason": "声母题错误",
                "question_ids": ["initial"],
                "activity": "拆分ma",
                "success_criterion": "声母m",
            }
        ]
        * 2,
    }
    AnalysisContent.model_validate(data).check_evidence(evidence(state))
    for key, value in [
        ("question_feedback", []),
        ("question_feedback", data["question_feedback"] * 2),
        ("practice_tasks", [{**data["practice_tasks"][0], "question_ids": ["invented"]}] * 2),
    ]:
        with pytest.raises(ValueError):
            AnalysisContent.model_validate({**data, key: value}).check_evidence(evidence(state))
    with pytest.raises(ValueError):
        AnalysisContent.model_validate({**data, "question_feedback": []}).check_evidence(
            evidence(finished())
        )


def test_dispatcher_routes_only_registered_assessment_events():
    from app.services.agents.dispatcher import AgentDispatcher

    agent = Mock(agent_id="assessment_review", prompt_version="test")
    agent.analyze.return_value = {"agent_id": "assessment_review"}
    dispatcher = AgentDispatcher([agent])
    payload = evidence(finished())
    assert dispatcher.run("assessment.completed", payload) == agent.analyze.return_value
    agent.analyze.assert_called_once_with(payload)
    with pytest.raises(ValueError):
        dispatcher.run("unit.completed", payload)
    assert agent.analyze.call_count == 1
    with pytest.raises(ValueError):
        AgentDispatcher([agent, agent])
