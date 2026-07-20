import json
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.exceptions import ExperienceNotFoundError
from app.repositories.experience_repository import ExperienceRepository
from app.schemas import (
    ErrorResponse,
    ExperienceCreate,
    ExperienceRead,
    OutcomeRead,
    OutcomeSubmit,
    SimilarExperienceRead,
)
from app.services.embedding_service import (
    EmbeddingProvider,
    build_embedding_text,
    get_embedding_service,
)
from app.services.retrieval_service import RetrievalService

router = APIRouter(prefix="/api/v1/experiences", tags=["experiences"])

DbSession = Annotated[Session, Depends(get_db)]
Embedder = Annotated[EmbeddingProvider, Depends(get_embedding_service)]


@router.post("", response_model=ExperienceRead, status_code=status.HTTP_201_CREATED)
def create_experience(data: ExperienceCreate, db: DbSession, embedder: Embedder) -> ExperienceRead:
    embedding = embedder.embed(build_embedding_text(data.task, data.proposed_action))
    experience = ExperienceRepository(db).create(data, embedding_json=json.dumps(embedding))
    return ExperienceRead.model_validate(experience)


@router.get("", response_model=list[ExperienceRead])
def list_experiences(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ExperienceRead]:
    experiences = ExperienceRepository(db).list(limit=limit, offset=offset)
    return [ExperienceRead.model_validate(e) for e in experiences]


# Declared before /{experience_id} so "similar" is not parsed as an ID.
@router.get("/similar", response_model=list[SimilarExperienceRead])
def find_similar_experiences(
    db: DbSession,
    embedder: Embedder,
    task: Annotated[str, Query(min_length=1, max_length=2000)],
    action: Annotated[str, Query(min_length=1, max_length=2000)],
    limit: Annotated[int, Query(ge=1, le=50)] = 5,
) -> list[SimilarExperienceRead]:
    query_embedding = embedder.embed(build_embedding_text(task, action))
    experiences = ExperienceRepository(db).all_with_embeddings()
    retrieval = RetrievalService(min_similarity=get_settings().min_similarity)
    results = retrieval.find_similar(query_embedding, experiences, limit=limit)
    return [
        SimilarExperienceRead(
            experience_id=r.experience.id,
            task=r.experience.task,
            proposed_action=r.experience.proposed_action,
            tool_name=r.experience.tool_name,
            similarity=round(r.similarity, 4),
            was_successful=(
                r.experience.outcome.was_successful if r.experience.outcome else None
            ),
        )
        for r in results
    ]


@router.get(
    "/{experience_id}",
    response_model=ExperienceRead,
    responses={404: {"model": ErrorResponse}},
)
def get_experience(experience_id: int, db: DbSession) -> ExperienceRead:
    experience = ExperienceRepository(db).get(experience_id)
    if experience is None:
        raise ExperienceNotFoundError(experience_id)
    return ExperienceRead.model_validate(experience)


@router.patch(
    "/{experience_id}/outcome",
    response_model=OutcomeRead,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def record_outcome(experience_id: int, data: OutcomeSubmit, db: DbSession) -> OutcomeRead:
    repo = ExperienceRepository(db)
    experience = repo.get(experience_id)
    if experience is None:
        raise ExperienceNotFoundError(experience_id)
    outcome = repo.add_outcome(experience, data)
    return OutcomeRead.model_validate(outcome)


@router.delete(
    "/{experience_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorResponse}},
)
def delete_experience(experience_id: int, db: DbSession) -> None:
    repo = ExperienceRepository(db)
    experience = repo.get(experience_id)
    if experience is None:
        raise ExperienceNotFoundError(experience_id)
    repo.delete(experience)
