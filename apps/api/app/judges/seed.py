"""Seed system judge rubric templates."""

from sqlalchemy.orm import Session

from app.judges.rubrics import SYSTEM_RUBRIC_TEMPLATES
from app.models.entities import JudgeRubricTemplate


def seed_judge_rubrics(db: Session) -> None:
    existing = db.query(JudgeRubricTemplate).filter(JudgeRubricTemplate.is_system.is_(True)).count()
    if existing:
        return
    for item in SYSTEM_RUBRIC_TEMPLATES:
        db.add(
            JudgeRubricTemplate(
                name=item["name"],
                description=item["description"],
                criteria=item["criteria"],
                version=1,
                is_system=True,
            )
        )
