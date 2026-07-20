import json
from dataclasses import dataclass

import numpy as np

from app.models import Experience


@dataclass
class RetrievedExperience:
    experience: Experience
    similarity: float


class RetrievalService:
    def __init__(self, min_similarity: float = 0.3) -> None:
        self.min_similarity = min_similarity

    def find_similar(
        self,
        query_embedding: list[float],
        experiences: list[Experience],
        limit: int = 5,
    ) -> list[RetrievedExperience]:
        candidates = [e for e in experiences if e.embedding]
        if not candidates:
            return []

        matrix = np.array([json.loads(e.embedding) for e in candidates], dtype=np.float64)
        query = np.array(query_embedding, dtype=np.float64)

        # Cosine similarity; guard against zero vectors.
        query_norm = np.linalg.norm(query)
        row_norms = np.linalg.norm(matrix, axis=1)
        if query_norm == 0:
            return []
        safe_row_norms = np.where(row_norms == 0, 1.0, row_norms)
        similarities = (matrix @ query) / (safe_row_norms * query_norm)
        similarities = np.where(row_norms == 0, 0.0, similarities)

        scored = [
            RetrievedExperience(experience=e, similarity=float(s))
            for e, s in zip(candidates, similarities, strict=True)
            if s >= self.min_similarity
        ]
        scored.sort(key=lambda r: r.similarity, reverse=True)
        return scored[:limit]
