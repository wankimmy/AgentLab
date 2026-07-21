"""Draft evaluation case generation from agent configuration."""

import uuid

from sqlalchemy.orm import Session

from app.models.entities import (
    AgentVersion,
    BackgroundJob,
    CaseSeverity,
    CaseStatus,
    EvaluationCase,
    EvaluationDatasetVersion,
    JobStatus,
)
from app.services.cost_service import estimate_cost


def estimate_generate_cost(db: Session, version: AgentVersion, count: int = 6) -> float:
    per = float(estimate_cost(db, version.provider, version.model, 400, 300))
    return per * count


def _topics_from_prompt(prompt: str) -> list[str]:
    lines = [ln.strip() for ln in prompt.splitlines() if ln.strip()]
    topics: list[str] = []
    for ln in lines:
        if ln.startswith("-") and len(ln) > 10:
            topics.append(ln.lstrip("- ").strip()[:120])
    if not topics:
        topics = ["General capability check", "Unsupported request handling", "Citation behaviour"]
    return topics[:8]


def build_draft_case_specs(version: AgentVersion, *, min_count: int = 6) -> list[dict]:
    topics = _topics_from_prompt(version.system_prompt or "")
    categories = ["correct", "unsupported", "citation", "tool", "security"]
    specs: list[dict] = []
    for i in range(max(min_count, len(topics))):
        cat = categories[i % len(categories)]
        topic = topics[i % len(topics)]
        specs.append(
            {
                "name": f"Generated: {topic[:40]}",
                "category": cat,
                "user_message": f"Regarding {topic}: what should the agent do?",
                "expected_behaviour": "Follow system prompt and refuse when unsupported.",
                "notes": "AI-generated draft — review before approving.",
            }
        )
    return specs


def generate_draft_cases_sync(
    db: Session,
    *,
    job_id: uuid.UUID | None,
    dataset_version_id: uuid.UUID,
    agent_version_id: uuid.UUID,
) -> list[uuid.UUID]:
    version = db.get(AgentVersion, agent_version_id)
    dv = db.get(EvaluationDatasetVersion, dataset_version_id)
    if not version or not dv:
        raise ValueError("Version or dataset version not found")

    job = db.get(BackgroundJob, job_id) if job_id else None
    if job:
        job.status = JobStatus.running

    created: list[uuid.UUID] = []
    try:
        for spec in build_draft_case_specs(version):
            case = EvaluationCase(
                dataset_version_id=dv.id,
                name=spec["name"],
                category=spec["category"],
                user_message=spec["user_message"],
                expected_behaviour=spec.get("expected_behaviour"),
                notes=spec.get("notes"),
                severity=CaseSeverity.medium,
                status=CaseStatus.draft,
            )
            db.add(case)
            db.flush()
            created.append(case.id)
        if job:
            job.status = JobStatus.completed
            job.payload = {**(job.payload or {}), "created_case_ids": [str(c) for c in created]}
    except Exception as exc:
        if job:
            job.status = JobStatus.failed
            job.error = str(exc)
        raise

    return created
