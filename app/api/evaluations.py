from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import EvaluationHistoryItem, EvaluationRead, ExperienceCreate
from app.services.embedding_service import EmbeddingProvider, get_embedding_service
from app.services.evaluation_service import EvaluationService

router = APIRouter(prefix="/api/v1/evaluations", tags=["evaluations"])

DbSession = Annotated[Session, Depends(get_db)]
Embedder = Annotated[EmbeddingProvider, Depends(get_embedding_service)]


@router.post("", response_model=EvaluationRead, status_code=status.HTTP_201_CREATED)
def evaluate_action(data: ExperienceCreate, db: DbSession, embedder: Embedder) -> EvaluationRead:
    return EvaluationService(db, embedder).evaluate(data)


@router.get("", response_model=list[EvaluationHistoryItem])
def list_evaluations(
    db: DbSession,
    embedder: Embedder,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[EvaluationHistoryItem]:
    evaluations = EvaluationService(db, embedder).history(limit=limit, offset=offset)
    return [EvaluationHistoryItem.model_validate(e) for e in evaluations]
