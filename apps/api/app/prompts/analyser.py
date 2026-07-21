"""Prompt structural analysis and improvement suggestions."""

import re
import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import (
    AgentVersion,
    BackgroundJob,
    JobStatus,
    PromptRecommendation,
    PromptRecommendationSource,
    PromptRecommendationStatus,
)


SECTION_CHECKS = [
    ("role", r"\bROLE\b", "Add a ROLE section describing the assistant identity."),
    ("objective", r"\bPRIMARY OBJECTIVE\b|\bOBJECTIVE\b", "State a PRIMARY OBJECTIVE."),
    ("prohibited", r"\bPROHIBITED\b", "List PROHIBITED BEHAVIOUR explicitly."),
    ("missing_info", r"\bWHEN INFORMATION IS MISSING\b", "Explain missing-information handling."),
    ("citations", r"\bCITATIONS?\b", "Add citation rules when using knowledge."),
]


def structural_suggestions(prompt: str) -> list[dict]:
    items: list[dict] = []
    for section_id, pattern, fix in SECTION_CHECKS:
        if not re.search(pattern, prompt, re.I):
            items.append(
                {
                    "type": "structure",
                    "section": section_id,
                    "title": f"Missing {section_id.replace('_', ' ')}",
                    "detail": fix,
                    "priority": "medium",
                }
            )
    if len(prompt) < 200:
        items.append(
            {
                "type": "length",
                "title": "Prompt may be too short",
                "detail": "Expand instructions with examples and escalation paths.",
                "priority": "low",
            }
        )
    return items


def llm_suggestions_mock(prompt: str) -> list[dict]:
    if settings.ai_api_key:
        return []
    return [
        {
            "type": "llm",
            "title": "Clarify refusal examples",
            "detail": "Add 1–2 example phrases for unsupported payroll or PII requests.",
            "priority": "high",
        },
        {
            "type": "llm",
            "title": "Tool usage guardrails",
            "detail": "Specify when calculator vs knowledge_search should be used.",
            "priority": "medium",
        },
    ]


def estimate_analyse_cost(version: AgentVersion) -> float:
    return 0.002 if settings.ai_api_key else 0.0


def analyse_prompt_sync(
    db: Session,
    *,
    job_id: uuid.UUID | None,
    agent_version_id: uuid.UUID,
    user_id: uuid.UUID,
    source: PromptRecommendationSource,
) -> uuid.UUID:
    version = db.get(AgentVersion, agent_version_id)
    if not version:
        raise ValueError("Agent version not found")

    job = db.get(BackgroundJob, job_id) if job_id else None
    if job:
        job.status = JobStatus.running

    prompt = version.system_prompt or ""
    suggestions = structural_suggestions(prompt) + llm_suggestions_mock(prompt)
    if source == PromptRecommendationSource.failed_cases:
        suggestions.insert(
            0,
            {
                "type": "failed_cases",
                "title": "Review failing eval cases",
                "detail": "Add explicit rules for categories that failed in the latest run.",
                "priority": "high",
            },
        )

    rec = PromptRecommendation(
        agent_version_id=version.id,
        source=source,
        suggestions=suggestions,
        status=PromptRecommendationStatus.draft,
        estimated_cost=Decimal(str(estimate_analyse_cost(version))),
        created_by=user_id,
    )
    db.add(rec)
    db.flush()

    if job:
        job.status = JobStatus.completed
        job.payload = {**(job.payload or {}), "recommendation_id": str(rec.id)}

    return rec.id
