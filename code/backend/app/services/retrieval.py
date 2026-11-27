"""Shared synchronous services; call in sync routes or bounded worker threads."""

import hashlib
import json
from typing import Protocol

from app.domain.retrieval.chunking import CHUNKER_VERSION, split_text
from app.integrations.embedding.client import Embedder, validate_vectors
from app.schemas.retrieval import (
    KnowledgeDocument,
    RetrievalFilters,
    RetrievalHit,
    RetrievalQuery,
    RetrievalResult,
)


class KnowledgeRepository(Protocol):
    def replace(self, document: KnowledgeDocument, fingerprint: str, embedding_key: str,
                chunks: list[str], vectors: list[list[float]]) -> list[str]: ...
    def delete(self, document_id: str) -> bool: ...
    def search(self, vector: list[float], embedding_key: str, filters: RetrievalFilters,
               limit: int) -> list[RetrievalHit]: ...


class IngestionService:
    def __init__(self, repository: KnowledgeRepository, embedder: Embedder):
        self.repository = repository
        self.embedder = embedder

    def ingest(self, document: KnowledgeDocument) -> list[str]:
        chunks = split_text(document.text)
        # Fail before any write; a failed batch leaves the old version available.
        vectors = validate_vectors(self.embedder.embed(chunks), len(chunks),
                                   self.embedder.dimensions)
        fingerprint = hashlib.sha256(json.dumps(
            {"document": document.model_dump(), "chunker": CHUNKER_VERSION},
            ensure_ascii=False, sort_keys=True,
        ).encode()).hexdigest()
        return self.repository.replace(document, fingerprint, self.embedder.key, chunks, vectors)

    def delete(self, document_id: str) -> bool:
        return self.repository.delete(document_id)


class RetrievalService:
    def __init__(self, repository: KnowledgeRepository, embedder: Embedder):
        self.repository = repository
        self.embedder = embedder

    def search(self, request: RetrievalQuery) -> RetrievalResult:
        vector = validate_vectors(self.embedder.embed([request.query]), 1,
                                  self.embedder.dimensions)[0]
        candidates = self.repository.search(vector, self.embedder.key, request.filters,
                                            request.top_k)
        hits = []
        remaining = request.max_context_chars
        for hit in candidates:
            if hit.score < request.min_score:
                continue
            if len(hit.text) > remaining:
                continue  # Keep whole source chunks, never silently truncate evidence.
            hits.append(hit)
            remaining -= len(hit.text)
        return RetrievalResult(hits=hits, embedding_key=self.embedder.key)
