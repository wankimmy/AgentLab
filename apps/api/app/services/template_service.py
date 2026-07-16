"""Shared agent creation from templates."""

import uuid
from copy import deepcopy

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.entities import Agent, AgentTemplate, AgentTemplateVersion, AgentVersion, User


def version_defaults_from_template(db: Session, template_id: uuid.UUID) -> dict:
    template = db.get(AgentTemplate, template_id)
    if not template or not template.current_version_id:
        raise HTTPException(status_code=404, detail="Template not found")
    tv = db.get(AgentTemplateVersion, template.current_version_id)
    if not tv:
        raise HTTPException(status_code=404, detail="Template version not found")
    return {
        "system_prompt": tv.system_prompt,
        "provider": tv.model_config_json.get("provider", "mock"),
        "model": tv.model_config_json.get("model", "mock-model"),
        "model_config_json": deepcopy(tv.model_config_json),
        "retrieval_config": deepcopy(tv.retrieval_config),
        "tool_config": deepcopy(tv.tool_config),
        "memory_config": deepcopy(tv.memory_config),
        "rag_enabled": bool(tv.retrieval_config.get("enabled", False)),
    }


def create_agent_from_template(
    db: Session,
    user: User,
    template_id: uuid.UUID,
    *,
    name: str | None = None,
    purpose: str | None = None,
    target_audience: str | None = None,
    notes: str | None = None,
    system_prompt_override: str | None = None,
    tool_config_override: dict | None = None,
) -> Agent:
    template = db.get(AgentTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    defaults = version_defaults_from_template(db, template_id)
    if system_prompt_override:
        defaults["system_prompt"] = system_prompt_override
    if tool_config_override:
        defaults["tool_config"] = tool_config_override

    agent = Agent(
        user_id=user.id,
        name=name or template.name,
        purpose=purpose,
        target_audience=target_audience,
        description=template.description,
        risk_level=template.risk_level,
        notes=notes,
        template_id=template.id,
    )
    db.add(agent)
    db.flush()

    version = AgentVersion(
        agent_id=agent.id,
        version_number=1,
        parent_version_id=None,
        change_summary=f"Created from template {template.slug}",
        **defaults,
    )
    db.add(version)
    db.flush()
    agent.active_version_id = version.id
    db.commit()
    db.refresh(agent)
    return agent


def get_template_by_slug(db: Session, slug: str) -> AgentTemplate | None:
    return db.query(AgentTemplate).filter(AgentTemplate.slug == slug).first()
