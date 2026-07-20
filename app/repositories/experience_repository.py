from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Experience
from app.schemas import ExperienceCreate


class ExperienceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, data: ExperienceCreate) -> Experience:
        experience = Experience(
            task=data.task,
            proposed_action=data.proposed_action,
            tool_name=data.tool_name.value,
            environment_context=data.environment_context,
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

    def delete(self, experience: Experience) -> None:
        self.db.delete(experience)
        self.db.commit()
