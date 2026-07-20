from functools import lru_cache
from typing import Protocol

from app.config import get_settings


def build_embedding_text(task: str, proposed_action: str) -> str:
    """Canonical text embedded for an experience; queries must use the same shape."""
    return f"Task: {task}\nAction: {proposed_action}"


class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> list[float]: ...


class SentenceTransformerEmbeddingService:
    """Local embeddings via sentence-transformers; the model loads lazily on first use
    so tests and cold API paths never trigger a model download."""

    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._model = None

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
        return self._model

    def embed(self, text: str) -> list[float]:
        vector = self._get_model().encode(text, normalize_embeddings=True)
        return [float(v) for v in vector]


@lru_cache
def get_embedding_service() -> SentenceTransformerEmbeddingService:
    return SentenceTransformerEmbeddingService(get_settings().embedding_model_name)
