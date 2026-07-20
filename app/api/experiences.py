from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import ExperienceNotFoundError
from app.repositories.experience_repository import ExperienceRepository
from app.schemas import ErrorResponse, ExperienceCreate, ExperienceRead

router = APIRouter(prefix="/api/v1/experiences", tags=["experiences"])

DbSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=ExperienceRead, status_code=status.HTTP_201_CREATED)
def create_experience(data: ExperienceCreate, db: DbSession) -> ExperienceRead:
    experience = ExperienceRepository(db).create(data)
    return ExperienceRead.model_validate(experience)


@router.get("", response_model=list[ExperienceRead])
def list_experiences(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ExperienceRead]:
    experiences = ExperienceRepository(db).list(limit=limit, offset=offset)
    return [ExperienceRead.model_validate(e) for e in experiences]


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
