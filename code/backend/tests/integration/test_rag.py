"""Real pgvector coverage. CI uses a pgvector-enabled isolated PostgreSQL database."""

import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.schema import CreateSchema, DropSchema

from app.core.config import Settings
from app.db.repositories.knowledge import (
    DocumentConflict,
    PostgresKnowledgeRepository,
    initialize_knowledge_schema,
)
from app.db.session import database_engine, initialize_schema
from app.integrations.embedding.client import EmbeddingUnavailable
from app.main import create_app
from app.schemas.retrieval import KnowledgeDocument, RetrievalQuery
from app.services.retrieval import IngestionService, RetrievalService
from tests.helpers import login


class FakeEmbedder:
    key = "test-two-dimensional-v1"
    dimensions = 2

    def embed(self, texts):
        return [[1.0, 0.0] if "声调" in t else [0.0, 1.0] for t in texts]


@pytest.fixture
def rag_db(pytestconfig):
    url = os.environ.get("OWL_TEST_DATABASE_URL")
    if not url and pytestconfig.getoption("--postgres"):
        url = Settings().database_url.get_secret_value()
    if not url:
        pytest.skip("Set OWL_TEST_DATABASE_URL to a pgvector-enabled test database")
    admin = database_engine(url)
    schema = "test_rag_" + uuid4().hex
    with admin.begin() as c:
        c.execute(text("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public"))
        c.execute(CreateSchema(schema))
    engine = database_engine(admin.url.update_query_dict({"options": f"-csearch_path={schema}"}))
    try:
        initialize_knowledge_schema(engine)
        initialize_knowledge_schema(engine)  # Explicit migration is repeatable.
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as c:
            c.execute(DropSchema(schema, cascade=True))
        admin.dispose()


def doc(document_id="tone", **changes):
    return KnowledgeDocument.model_validate({
        "document_id": document_id, "title": "声调说明", "text": "声调练习。",
        "source": "team", "license": "test", "content_version": 1,
        "review_status": "approved", "visibility": "public", "language": "zh",
        "direction_ids": ["daily"], "knowledge_point_ids": ["tone"], **changes,
    })


def test_vector_lifecycle_filtering_and_restart(rag_db):
    repo = PostgresKnowledgeRepository(rag_db)
    ingestion = IngestionService(repo, FakeEmbedder())
    service = RetrievalService(repo, FakeEmbedder())
    ids = ingestion.ingest(doc())
    assert ingestion.ingest(doc()) == ids
    ingestion.ingest(doc("travel", text="旅游练习。", direction_ids=["travel"]))
    for name, changes in [("draft", {"review_status": "draft"}),
                          ("internal", {"visibility": "internal"}),
                          ("answer", {"answer_visibility": "answer"})]:
        ingestion.ingest(doc(name, **changes))
    result = service.search(RetrievalQuery(query="声调", min_score=.5))
    assert [h.document_id for h in result.hits] == ["tone"]
    assert result.hits[0].score == pytest.approx(1)
    assert not service.search(RetrievalQuery(query="声调", filters={"language": "en"})).hits
    assert not service.search(RetrievalQuery(query="声调", filters={
        "direction_id": "unknown",
    })).hits
    assert service.search(RetrievalQuery(query="声调", filters={
        "knowledge_point_id": "tone", "document_id": "tone",
    })).hits
    with pytest.raises(DocumentConflict):
        ingestion.ingest(doc(text="声调改写。"))
    ingestion.ingest(doc(text="声调新版。", content_version=2))
    with pytest.raises(DocumentConflict):
        ingestion.ingest(doc())
    # Recreate services/connection pool; persistence is in PostgreSQL.
    rag_db.dispose()
    restarted = RetrievalService(PostgresKnowledgeRepository(rag_db), FakeEmbedder())
    hits = restarted.search(RetrievalQuery(query="声调", min_score=.5)).hits
    assert len(hits) == 1 and hits[0].content_version == 2
    assert hits[0].text == "声调新版。"
    assert ingestion.delete("tone")
    assert not restarted.search(RetrievalQuery(query="声调", min_score=.5)).hits
    with rag_db.connect() as c:
        assert c.scalar(text("SELECT count(*) FROM rag_chunks WHERE document_id='tone'")) == 0


def test_atomic_failure_and_embedding_version_isolation(rag_db):
    repo = PostgresKnowledgeRepository(rag_db)
    ingestion = IngestionService(repo, FakeEmbedder())
    ingestion.ingest(doc())
    # Malformed write fails after DELETE; transaction must restore the old chunks and version.
    with pytest.raises(ValueError):
        repo.replace(doc(content_version=2), "new", FakeEmbedder.key, ["new"], [])
    assert RetrievalService(repo, FakeEmbedder()).search(RetrievalQuery(query="声调")).hits
    other = FakeEmbedder()
    other.key = "new-model"
    assert not RetrievalService(repo, other).search(RetrievalQuery(query="声调")).hits
    IngestionService(repo, other).ingest(doc())  # Reindex same document with new embedding model.
    assert RetrievalService(repo, other).search(RetrievalQuery(query="声调")).hits


def test_enabled_app_returns_persisted_sources(rag_db, tmp_path):
    initialize_schema(rag_db)
    IngestionService(PostgresKnowledgeRepository(rag_db), FakeEmbedder()).ingest(doc())
    settings = Settings(
        _env_file=None, database_url=rag_db.url.render_as_string(hide_password=False),
        rag_enabled=True, owl_learning_file=tmp_path / "learning.json",
        owl_log_file=tmp_path / "app.log",
    )
    app = create_app(settings=settings)
    app.state.retrieval.embedder = FakeEmbedder()
    with TestClient(app) as client:
        login(client)
        response = client.post("/api/v1/knowledge/search", json={"query": "声调"})
        assert response.status_code == 200
        hit = response.json()["hits"][0]
        assert hit["document_id"] == "tone"
        assert hit["source"] == "team"
        assert hit["content_version"] == 1
        assert response.headers["Cache-Control"] == "no-store"


def test_authenticated_http_contract(tmp_path):
    settings = Settings(_env_file=None, database_url="", deepseek_api_key="",
                        owl_log_file=tmp_path / "app.log")
    with TestClient(create_app(tmp_path / "accounts.json", settings)) as client:
        assert client.post("/api/v1/knowledge/search", json={"query": "声调"}).status_code == 401
        login(client)
        assert client.post("/api/v1/knowledge/search", json={"query": "声调"}).status_code == 503

        class Service:
            def search(self, request):
                raise EmbeddingUnavailable("upstream secret")

        client.app.state.retrieval = Service()
        response = client.post("/api/v1/knowledge/search", json={"query": "声调"})
        assert response.status_code == 503
        assert "secret" not in response.text
        assert client.post("/api/v1/knowledge/search", json={"query": " "}).status_code == 422
        assert client.post("/api/v1/knowledge/search", json={"query": "声调"},
                           headers={"Origin": "https://evil.test"}).status_code == 403


@pytest.mark.parametrize("payload_change", [
    {"text": " "}, {"text": "甲" * 200_001}, {"content_version": 0},
    {"review_status": "unchecked"}, {"unknown": "field"},
])
def test_ingestion_rejects_invalid_documents(tmp_path, payload_change):
    from unittest.mock import Mock
    from uuid import UUID

    settings = Settings(_env_file=None, database_url="", rag_enabled=False,
                        owl_log_file=tmp_path / "app.log")
    app = create_app(tmp_path / "accounts.json", settings)
    with TestClient(app) as client:
        login(client)
        settings.rag_ingest_user_ids = [UUID(client.get("/api/v1/auth/me").json()["id"])]
        service = Mock()
        app.state.ingestion = service
        response = client.post("/api/v1/knowledge/documents", json={
            **doc().model_dump(), **payload_change,
        })
        assert response.status_code == 422
        service.ingest.assert_not_called()


def test_ingestion_access_disabled_service_and_sanitized_errors(tmp_path):
    from unittest.mock import Mock
    from uuid import UUID

    from sqlalchemy.exc import SQLAlchemyError

    settings = Settings(_env_file=None, database_url="", rag_enabled=False,
                        owl_log_file=tmp_path / "app.log")
    app = create_app(tmp_path / "accounts.json", settings)
    payload = doc().model_dump()
    with TestClient(app) as client:
        assert client.post("/api/v1/knowledge/documents", json=payload).status_code == 401
        login(client)
        service = Mock()
        app.state.ingestion = service
        assert client.post("/api/v1/knowledge/documents", json=payload).status_code == 403
        service.ingest.assert_not_called()
        settings.rag_ingest_user_ids = [UUID(client.get("/api/v1/auth/me").json()["id"])]
        for headers in ({"Origin": "https://evil.test"}, {"Sec-Fetch-Site": "cross-site"}):
            assert client.post("/api/v1/knowledge/documents", json=payload,
                               headers=headers).status_code == 403
        service.ingest.assert_not_called()
        app.state.ingestion = None
        assert client.post("/api/v1/knowledge/documents", json=payload).status_code == 503
        app.state.ingestion = service
        for error, status in [(DocumentConflict("secret document"), 409),
                              (EmbeddingUnavailable("secret API key"), 503),
                              (SQLAlchemyError("secret database password"), 503)]:
            service.ingest.side_effect = error
            response = client.post("/api/v1/knowledge/documents", json=payload)
            assert response.status_code == status
            assert "secret" not in response.text


def test_http_ingest_search_update_and_failure_preserves_previous_version(rag_db, tmp_path):
    from uuid import UUID

    initialize_schema(rag_db)
    settings = Settings(
        _env_file=None, database_url=rag_db.url.render_as_string(hide_password=False),
        rag_enabled=True, owl_learning_file=tmp_path / "learning.json",
        owl_log_file=tmp_path / "app.log",
    )
    app = create_app(settings=settings)
    app.state.ingestion.embedder = FakeEmbedder()
    app.state.retrieval.embedder = FakeEmbedder()
    with TestClient(app) as client:
        login(client)
        settings.rag_ingest_user_ids = [UUID(client.get("/api/v1/auth/me").json()["id"])]
        # Default draft/internal metadata must not become publicly searchable on ingestion.
        draft = doc(review_status="draft", visibility="internal").model_dump()
        response = client.post("/api/v1/knowledge/documents", json=draft)
        assert response.status_code == 200
        assert response.json() == {
            "document_id": "tone", "content_version": 1, "chunk_count": 1,
            "chunk_ids": ["tone:v1:0"], "embedding_key": FakeEmbedder.key,
        }
        assert response.headers["Cache-Control"] == "no-store"
        assert not client.post("/api/v1/knowledge/search", json={"query": "声调"}).json()["hits"]
        # Publish version 2 with several chunks; complete ingest must precede success response.
        published = doc(content_version=2, text="声调练习。" * 300).model_dump()
        response = client.post("/api/v1/knowledge/documents", json=published)
        assert response.status_code == 200 and response.json()["chunk_count"] > 1
        ids = response.json()["chunk_ids"]
        assert client.post("/api/v1/knowledge/documents", json=published).json()["chunk_ids"] == ids
        hits = client.post("/api/v1/knowledge/search", json={"query": "声调"}).json()["hits"]
        assert hits and all(h["content_version"] == 2 for h in hits)
        assert client.post("/api/v1/knowledge/documents", json=draft).status_code == 409
        changed_same_version = {**published, "text": "声调修改。"}
        assert client.post("/api/v1/knowledge/documents",
                           json=changed_same_version).status_code == 409

        class OfflineEmbedder(FakeEmbedder):
            def embed(self, texts):
                raise EmbeddingUnavailable("secret API error")

        app.state.ingestion.embedder = OfflineEmbedder()
        response = client.post("/api/v1/knowledge/documents", json={
            **published, "content_version": 3,
        })
        assert response.status_code == 503 and "secret" not in response.text
        hits = client.post("/api/v1/knowledge/search", json={"query": "声调"}).json()["hits"]
        assert hits and all(h["content_version"] == 2 for h in hits)
