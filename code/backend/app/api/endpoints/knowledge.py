"""Authenticated retrieval and allowlisted document ingestion."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import (
    KnowledgeEditor,
    User,
    ingestion_service,
    retrieval_service,
    same_origin,
)
from app.db.repositories.knowledge import DocumentConflict
from app.integrations.embedding.client import EmbeddingUnavailable
from app.schemas.retrieval import (
    IngestionResult,
    KnowledgeDocument,
    RetrievalQuery,
    RetrievalResult,
)
from app.services.retrieval import IngestionService, RetrievalService

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


@router.post("/documents", response_model=IngestionResult, dependencies=[Depends(same_origin)])
def ingest_document(body: KnowledgeDocument, user: KnowledgeEditor,
                    service: Annotated[IngestionService, Depends(ingestion_service)]):
    try:
        ids = service.ingest(body)
    except DocumentConflict:
        raise HTTPException(409, "文档版本冲突，请检查当前版本并递增 content_version。") from None
    except (EmbeddingUnavailable, SQLAlchemyError):
        raise HTTPException(503, "文档入库暂不可用，请稍后重试。") from None
    return IngestionResult(
        document_id=body.document_id, content_version=body.content_version,
        chunk_count=len(ids), chunk_ids=ids, embedding_key=service.embedder.key,
    )


@router.post("/search", response_model=RetrievalResult, dependencies=[Depends(same_origin)])
def search(body: RetrievalQuery, user: User,
           service: Annotated[RetrievalService, Depends(retrieval_service)]):
    try:
        return service.search(body)
    except (EmbeddingUnavailable, SQLAlchemyError):
        raise HTTPException(503, "知识检索暂不可用，请稍后重试。") from None
