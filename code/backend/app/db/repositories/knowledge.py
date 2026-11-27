"""PostgreSQL + pgvector repository. Atomic replacement, exact cosine retrieval."""

import json

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.schemas.retrieval import KnowledgeDocument, RetrievalFilters, RetrievalHit


class DocumentConflict(ValueError):
    pass


DDL = [
    "CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public",
    """CREATE TABLE IF NOT EXISTS rag_schema_versions (
        version integer PRIMARY KEY CHECK (version = 1))""",
    """CREATE TABLE IF NOT EXISTS rag_documents (
        document_id text PRIMARY KEY, content_version integer NOT NULL,
        fingerprint text NOT NULL, embedding_key text NOT NULL, spec jsonb NOT NULL,
        updated_at timestamptz NOT NULL DEFAULT now())""",
    """CREATE TABLE IF NOT EXISTS rag_chunks (
        chunk_id text PRIMARY KEY,
        document_id text NOT NULL REFERENCES rag_documents(document_id) ON DELETE CASCADE,
        ordinal integer NOT NULL, content text NOT NULL, embedding public.vector NOT NULL,
        UNIQUE(document_id, ordinal))""",
    "CREATE INDEX IF NOT EXISTS rag_chunks_document_idx ON rag_chunks(document_id)",
    "INSERT INTO rag_schema_versions(version) VALUES (1) ON CONFLICT DO NOTHING",
]


def initialize_knowledge_schema(engine: Engine):
    # Separate from account migrations: no extension or schema writes at API startup.
    with engine.begin() as connection:
        connection.execute(text("SELECT pg_advisory_xact_lock(760019002)"))
        for statement in DDL:
            connection.execute(text(statement))


class PostgresKnowledgeRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    def replace(self, document: KnowledgeDocument, fingerprint: str, embedding_key: str,
                chunks: list[str], vectors: list[list[float]]) -> list[str]:
        ids = [f"{document.document_id}:v{document.content_version}:{i}"
               for i in range(len(chunks))]
        with self.engine.begin() as connection:
            connection.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:id, 0))"),
                               {"id": "rag:" + document.document_id})
            old = connection.execute(text(
                "SELECT * FROM rag_documents WHERE document_id=:id FOR UPDATE"
            ), {"id": document.document_id}).mappings().first()
            if old:
                if old["content_version"] > document.content_version:
                    raise DocumentConflict("Cannot replace a newer document version")
                if old["content_version"] == document.content_version:
                    if old["fingerprint"] != fingerprint:
                        raise DocumentConflict("Changed content/metadata requires a new version")
                    if old["embedding_key"] == embedding_key:
                        return ids
            connection.execute(text("""
                INSERT INTO rag_documents(document_id, content_version, fingerprint,
                    embedding_key, spec)
                VALUES (:id, :version, :fingerprint, :key, CAST(:spec AS jsonb))
                ON CONFLICT(document_id) DO UPDATE SET
                    content_version=excluded.content_version, fingerprint=excluded.fingerprint,
                    embedding_key=excluded.embedding_key, spec=excluded.spec, updated_at=now()
            """), {"id": document.document_id, "version": document.content_version,
                    "fingerprint": fingerprint, "key": embedding_key,
                    "spec": document.model_dump_json(exclude={"text"})})
            connection.execute(text("DELETE FROM rag_chunks WHERE document_id=:id"),
                               {"id": document.document_id})
            connection.execute(text("""
                INSERT INTO rag_chunks(chunk_id, document_id, ordinal, content, embedding)
                VALUES (:chunk_id, :id, :ordinal, :content, CAST(:vector AS public.vector))
            """), [{"chunk_id": chunk_id, "id": document.document_id, "ordinal": i,
                     "content": chunk, "vector": json.dumps(vector)}
                    for i, (chunk_id, chunk, vector) in
                    enumerate(zip(ids, chunks, vectors, strict=True))])
        return ids

    def delete(self, document_id: str) -> bool:
        with self.engine.begin() as connection:
            connection.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:id, 0))"),
                               {"id": "rag:" + document_id})
            result = connection.execute(text("DELETE FROM rag_documents WHERE document_id=:id"),
                                        {"id": document_id})
            return result.rowcount > 0

    def search(self, vector: list[float], embedding_key: str, filters: RetrievalFilters,
               limit: int) -> list[RetrievalHit]:
        # Visibility is enforced here; callers cannot request drafts/internal/answer material.
        required = {"review_status": "approved", "visibility": "public",
                    "answer_visibility": "teaching"}
        if filters.language:
            required["language"] = filters.language
        if filters.difficulty is not None:
            required["difficulty"] = filters.difficulty
        if filters.direction_id:
            required["direction_ids"] = [filters.direction_id]
        if filters.knowledge_point_id:
            required["knowledge_point_ids"] = [filters.knowledge_point_id]
        with self.engine.connect() as connection:
            rows = connection.execute(text("""
                SELECT c.chunk_id, c.document_id, c.content, d.spec,
                       1 - (c.embedding OPERATOR(public.<=>)
                            CAST(:vector AS public.vector)) AS score
                FROM rag_chunks c JOIN rag_documents d USING(document_id)
                WHERE d.embedding_key=:key AND d.spec @> CAST(:required AS jsonb)
                  AND (CAST(:document_id AS text) IS NULL OR d.document_id=:document_id)
                ORDER BY c.embedding OPERATOR(public.<=>) CAST(:vector AS public.vector), c.chunk_id
                LIMIT :limit
            """), {"vector": json.dumps(vector), "key": embedding_key,
                    "required": json.dumps(required), "document_id": filters.document_id,
                    "limit": limit}).mappings().all()
        return [RetrievalHit(
            chunk_id=row["chunk_id"], document_id=row["document_id"], text=row["content"],
            score=row["score"], **{key: row["spec"][key] for key in
                                   ("title", "source", "license", "content_version")},
        ) for row in rows]
