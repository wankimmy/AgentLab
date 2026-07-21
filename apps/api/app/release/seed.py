"""Seed release threshold templates."""

from sqlalchemy.orm import Session

from app.models.entities import ReleaseThresholdTemplate
from app.seed_data import ERP_RELEASE_THRESHOLDS

SYSTEM_TEMPLATES = [
    {
        "name": "ERP Release Gate",
        "description": "Default ERP support release thresholds.",
        "rules": {
            **ERP_RELEASE_THRESHOLDS,
            "no_critical_regressions": True,
            "no_security_regressions": True,
        },
    },
    {
        "name": "Standard Release",
        "description": "General pass rate and regression gates.",
        "rules": {
            "pass_rate": 0.85,
            "critical_pass_rate": 1.0,
            "no_critical_regressions": True,
            "no_security_regressions": True,
        },
    },
]


def seed_release_thresholds(db: Session) -> None:
    existing = (
        db.query(ReleaseThresholdTemplate)
        .filter(ReleaseThresholdTemplate.is_system.is_(True))
        .count()
    )
    if existing:
        return
    for item in SYSTEM_TEMPLATES:
        db.add(
            ReleaseThresholdTemplate(
                name=item["name"],
                description=item["description"],
                rules=item["rules"],
                version=1,
                is_system=True,
            )
        )
