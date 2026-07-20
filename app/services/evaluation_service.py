import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Evaluation
from app.repositories.experience_repository import ExperienceRepository
from app.schemas import (
    EvaluationRead,
    ExperienceCreate,
    SimilarEvidence,
)
from app.services.embedding_service import EmbeddingProvider, build_embedding_text
from app.services.retrieval_service import RetrievalService
from app.services.scoring_service import Evidence, ScoringService

DECISION_TO_STATUS = {"approve": "approved", "revise": "revised", "block": "blocked"}


class EvaluationService:
    def __init__(self, db: Session, embedder: EmbeddingProvider) -> None:
        self.db = db
        self.embedder = embedder
        self.settings = get_settings()

    def evaluate(self, data: ExperienceCreate) -> EvaluationRead:
        repo = ExperienceRepository(self.db)

        query_embedding = self.embedder.embed(
            build_embedding_text(data.task, data.proposed_action)
        )
        retrieved = RetrievalService(min_similarity=self.settings.min_similarity).find_similar(
            query_embedding,
            repo.all_with_embeddings(),
            limit=self.settings.retrieval_limit,
        )

        # Only experiences with recorded outcomes count as scoring evidence.
        evidence = [
            Evidence(similarity=r.similarity, was_successful=r.experience.outcome.was_successful)
            for r in retrieved
            if r.experience.outcome is not None
        ]
        result = ScoringService(
            approve_threshold=self.settings.approve_threshold,
            block_threshold=self.settings.block_threshold,
        ).score(
            evidence,
            tool_reliability=repo.tool_success_rate(data.tool_name.value),
            tool_name=data.tool_name.value,
        )

        # Record the proposed action itself so its outcome can be reported later.
        experience = repo.create(data, embedding_json=json.dumps(query_embedding))
        experience.status = DECISION_TO_STATUS[result.decision]
        evaluation = Evaluation(
            experience_id=experience.id,
            confidence=result.confidence,
            decision=result.decision,
            evidence_count=result.evidence_count,
            scoring_version=result.scoring_version,
        )
        self.db.add(evaluation)
        self.db.commit()
        self.db.refresh(evaluation)

        return EvaluationRead(
            evaluation_id=evaluation.id,
            experience_id=experience.id,
            decision=result.decision,
            confidence=result.confidence,
            reason=result.reason,
            evidence_count=result.evidence_count,
            similar_experiences=[
                SimilarEvidence(
                    experience_id=r.experience.id,
                    similarity=round(r.similarity, 4),
                    was_successful=(
                        r.experience.outcome.was_successful if r.experience.outcome else None
                    ),
                )
                for r in retrieved
            ],
            scoring_version=result.scoring_version,
        )

    def history(self, limit: int = 100, offset: int = 0) -> list[Evaluation]:
        stmt = (
            select(Evaluation)
            .order_by(Evaluation.created_at.desc(), Evaluation.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.scalars(stmt).all())
