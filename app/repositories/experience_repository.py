from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Experience, Outcome
from app.schemas import ExperienceCreate


class ExperienceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, data: ExperienceCreate, embedding_json: str | None = None) -> Experience:
        experience = Experience(
            task=data.task,
            proposed_action=data.proposed_action,
            tool_name=data.tool_name.value,
            environment_context=data.environment_context,
            embedding=embedding_json,
        )
        self.db.add(experience)
        self.db.commit()
        self.db.refresh(experience)
        return experience

    def get(self, experience_id: int) -> Experience | None:
        return self.db.get(Experience, experience_id)

    def list(self, limit: int = 100, offset: int = 0) -> list[Experience]:
        stmt = (
            select(Experience)
            .order_by(Experience.created_at.desc(), Experience.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.scalars(stmt).all())

    # Quoted annotation: the `list` method above shadows the builtin in this class body.
    def all_with_embeddings(self) -> "list[Experience]":
        stmt = select(Experience).where(Experience.embedding.is_not(None))
        return list(self.db.scalars(stmt).all())

    def tool_success_rate(self, tool_name: str) -> float | None:
        stmt = (
            select(Outcome.was_successful)
            .join(Experience, Outcome.experience_id == Experience.id)
            .where(Experience.tool_name == tool_name)
        )
        outcomes = list(self.db.scalars(stmt).all())
        if not outcomes:
            return None
        return sum(1 for o in outcomes if o) / len(outcomes)

    def delete(self, experience: Experience) -> None:
        self.db.delete(experience)
        self.db.commit()
