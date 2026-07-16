import hashlib
import math
from typing import Protocol

import httpx

from app.core.config import settings


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class MockEmbeddingProvider:
    """Deterministic unit vectors for CI."""

    def __init__(self, dimensions: int = 1536) -> None:
        self.dimensions = dimensions

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            digest = hashlib.sha256(text.encode()).digest()
            raw = [digest[i % len(digest)] / 255.0 for i in range(self.dimensions)]
            norm = math.sqrt(sum(x * x for x in raw)) or 1.0
            vectors.append([x / norm for x in raw])
        return vectors


class OpenAICompatibleEmbeddingProvider:
    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{self.base_url}/v1/embeddings",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "input": texts},
            )
            response.raise_for_status()
            data = response.json()
        items = sorted(data["data"], key=lambda x: x["index"])
        return [item["embedding"] for item in items]


def get_embedding_provider() -> EmbeddingProvider:
    if settings.embedding_api_key:
        return OpenAICompatibleEmbeddingProvider(
            base_url=settings.embedding_base_url,
            api_key=settings.embedding_api_key,
            model=settings.embedding_model,
        )
    return MockEmbeddingProvider(dimensions=settings.embedding_dimensions)
