import json
from unittest.mock import Mock

import httpx
import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.domain.retrieval.chunking import split_text
from app.integrations.embedding.client import (
    CompatibleEmbedder,
    EmbeddingUnavailable,
    validate_vectors,
)
from app.schemas.retrieval import KnowledgeDocument, RetrievalHit, RetrievalQuery
from app.services.retrieval import IngestionService, RetrievalService


def document(**changes):
    return KnowledgeDocument.model_validate({
        "document_id": "tone", "title": "声调", "text": "你好。",
        "source": "team", "license": "test", "content_version": 1, **changes,
    })


def test_chunking_bounds_coverage_and_determinism():
    original = "# 标题\r\n\r\n" + "甲乙丙丁戊己庚辛壬癸" * 400
    chunks = split_text(original)
    assert chunks == split_text(original)
    assert all(0 < len(c) <= 1000 for c in chunks)
    # Adjacent chunks preserve the configured overlap, including unbroken Chinese text.
    assert chunks[0][-100:] == chunks[1][:100]
    assert chunks[-1].endswith("壬癸")
    assert split_text("  ") == []
    assert split_text("第一段。\n\n第二段。") == ["第一段。\n\n第二段。"]


@pytest.mark.parametrize("vectors", [[[0, 0]], [[1]], [[float('nan'), 1]],
                                     [[True, 1]], [], [[float('inf'), 1]]])
def test_reject_invalid_vectors(vectors):
    with pytest.raises(ValueError):
        validate_vectors(vectors, 1, 2)


def test_embedding_batch_order_and_model_identity():
    calls = []

    def handler(request):
        payload = json.loads(request.content)
        calls.append(payload)
        assert request.url.path == "/v1/embeddings"
        return httpx.Response(200, json={"data": [
            {"index": i, "embedding": [float(i + 1), 1.0]}
            for i in reversed(range(len(payload["input"])))
        ]})

    settings = Settings(_env_file=None, rag_embedding_base_url="https://example.test/v1",
                        rag_embedding_api_key="secret", rag_embedding_dimensions=2,
                        rag_embedding_batch_size=2)
    embedder = CompatibleEmbedder(settings, transport=httpx.MockTransport(handler))
    assert embedder.embed(["甲", "乙", "丙"]) == [[1, 1], [2, 1], [1, 1]]
    assert [len(call["input"]) for call in calls] == [2, 1]
    assert calls[0]["dimensions"] == 2
    assert embedder.key != CompatibleEmbedder(
        settings.model_copy(update={"rag_embedding_revision": "2"}),
    ).key


@pytest.mark.parametrize("payload", [
    {"data": [{"index": 0, "embedding": [1, 1]}, {"index": 0, "embedding": [1, 1]}]},
    {"data": [{"index": 0, "embedding": [1]}]},
    {"data": "bad"},
])
def test_embedding_malformed_response_is_sanitized(payload):
    settings = Settings(_env_file=None, rag_embedding_base_url="https://example.test/v1",
                        rag_embedding_api_key="secret", rag_embedding_dimensions=2)
    embedder = CompatibleEmbedder(settings, transport=httpx.MockTransport(
        lambda request: httpx.Response(200, json=payload),
    ))
    with pytest.raises(EmbeddingUnavailable) as exc:
        embedder.embed(["甲"])
    assert "secret" not in str(exc.value)


def test_failed_embedding_does_not_write():
    repo = Mock()
    embedder = Mock(key="fake-v1", dimensions=2)
    embedder.embed.side_effect = EmbeddingUnavailable("offline")
    with pytest.raises(EmbeddingUnavailable):
        IngestionService(repo, embedder).ingest(document())
    repo.replace.assert_not_called()


def test_search_budget_score_and_provenance():
    repo = Mock()
    embedder = Mock(key="fake-v1", dimensions=2)
    embedder.embed.return_value = [[1, 0]]
    repo.search.return_value = [RetrievalHit(
        chunk_id=str(i), document_id="tone", title="声调", text="甲" * length,
        source="team", license="test", content_version=1, score=score,
    ) for i, (length, score) in enumerate([(150, .9), (150, .8), (20, -.1)])]
    result = RetrievalService(repo, embedder).search(RetrievalQuery(
        query="你好", max_context_chars=200,
    ))
    assert [h.chunk_id for h in result.hits] == ["0"]
    assert result.hits[0].source == "team"
    assert result.embedding_key == "fake-v1"


@pytest.mark.parametrize("changes", [{"query": " "}, {"top_k": 100},
                                     {"filters": {"visibility": "internal"}}])
def test_query_contract(changes):
    with pytest.raises(ValidationError):
        RetrievalQuery.model_validate({"query": "你好", **changes})
