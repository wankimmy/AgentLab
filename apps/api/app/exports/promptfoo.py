"""Promptfoo export from dataset and agent version."""

import uuid

import yaml
from sqlalchemy.orm import Session

from app.models.entities import AgentVersion, EvaluationCase, EvaluationDataset, EvaluationDatasetVersion


def build_promptfoo_config(
    db: Session,
    *,
    dataset_id: uuid.UUID,
    agent_version_id: uuid.UUID,
    dataset_version_id: uuid.UUID | None = None,
) -> dict:
    dataset = db.get(EvaluationDataset, dataset_id)
    version = db.get(AgentVersion, agent_version_id)
    if not dataset or not version:
        raise ValueError("Dataset or agent version not found")

    if dataset_version_id:
        dv = db.get(EvaluationDatasetVersion, dataset_version_id)
    else:
        dv = (
            db.query(EvaluationDatasetVersion)
            .filter(EvaluationDatasetVersion.dataset_id == dataset_id)
            .order_by(EvaluationDatasetVersion.version_number.desc())
            .first()
        )
    if not dv:
        raise ValueError("Dataset version not found")

    cases = (
        db.query(EvaluationCase)
        .filter(EvaluationCase.dataset_version_id == dv.id)
        .order_by(EvaluationCase.name)
        .all()
    )

    tests = [
        {
            "vars": {"query": c.user_message},
            "assert": [{"type": "contains", "value": kw} for kw in (c.required_keywords or [])[:3]]
            or [{"type": "javascript", "value": "output.length > 0"}],
            "metadata": {"case_id": str(c.id), "category": c.category, "name": c.name},
        }
        for c in cases
    ]

    return {
        "description": f"AgentLab export: {dataset.name}",
        "prompts": [version.system_prompt or "You are a helpful assistant."],
        "providers": [{"id": f"{version.provider}:{version.model}"}],
        "tests": tests,
    }


def export_promptfoo_yaml(db: Session, **kwargs) -> str:
    return yaml.safe_dump(build_promptfoo_config(db, **kwargs), sort_keys=False)
