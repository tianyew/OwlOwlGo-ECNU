"""Bounded OpenAI-compatible embedding adapter, independent of chat models."""

import hashlib
import math
from typing import Protocol

import httpx

from app.core.config import Settings


class EmbeddingUnavailable(Exception):
    pass


class Embedder(Protocol):
    key: str
    dimensions: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


def validate_vectors(vectors, count: int, dimensions: int) -> list[list[float]]:
    if not isinstance(vectors, list) or len(vectors) != count:
        raise ValueError("Embedding count mismatch")
    for vector in vectors:
        if not isinstance(vector, list) or len(vector) != dimensions:
            raise ValueError("Embedding dimension mismatch")
        if any(type(x) not in (int, float) or not math.isfinite(x) for x in vector):
            raise ValueError("Non-finite embedding")
        norm = math.hypot(*vector)
        if not math.isfinite(norm) or norm == 0:
            raise ValueError("Invalid embedding norm")
    return vectors


class CompatibleEmbedder:
    def __init__(self, settings: Settings, *, transport: httpx.BaseTransport | None = None):
        self.settings = settings
        self.transport = transport
        self.dimensions = settings.rag_embedding_dimensions
        identity = (f"{settings.rag_embedding_base_url.rstrip('/')}|"
                    f"{settings.rag_embedding_model}|{self.dimensions}|"
                    f"{settings.rag_embedding_revision}")
        self.key = hashlib.sha256(identity.encode()).hexdigest()

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        settings = self.settings
        key = settings.rag_embedding_api_key.get_secret_value().strip()
        base_url = settings.rag_embedding_base_url.rstrip("/")
        if not key or not base_url or not settings.rag_embedding_model:
            raise EmbeddingUnavailable("请配置 RAG Embedding 的地址、模型和密钥。")
        try:
            vectors = []
            with httpx.Client(timeout=settings.rag_embedding_timeout,
                              transport=self.transport, follow_redirects=False) as client:
                for start in range(0, len(texts), settings.rag_embedding_batch_size):
                    batch = texts[start:start + settings.rag_embedding_batch_size]
                    response = client.post(
                        base_url + "/embeddings",
                        headers={"Authorization": f"Bearer {key}"},
                        json={"model": settings.rag_embedding_model, "input": batch,
                              "dimensions": self.dimensions, "encoding_format": "float"},
                    )
                    response.raise_for_status()
                    data = response.json()["data"]
                    indices = [item["index"] for item in data]
                    if (any(type(i) is not int for i in indices)
                            or sorted(indices) != list(range(len(batch)))):
                        raise ValueError("Invalid embedding indices")
                    ordered = sorted(data, key=lambda item: item["index"])
                    vectors.extend(validate_vectors(
                        [item["embedding"] for item in ordered], len(batch), self.dimensions,
                    ))
            return vectors
        except (httpx.HTTPError, ValueError, KeyError, TypeError, OverflowError):
            raise EmbeddingUnavailable("向量服务暂不可用或返回格式不匹配。") from None
