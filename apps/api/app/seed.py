"""Seed owner user, tools, and agent templates."""

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models.entities import (
    AgentTemplate,
    AgentTemplateVersion,
    RiskLevel,
    Tool,
    User,
    UserRole,
)

TOOLS = [
    {
        "name": "calculator",
        "description": "Evaluate a mathematical expression safely.",
        "input_schema": {
            "type": "object",
            "properties": {"expression": {"type": "string"}},
            "required": ["expression"],
        },
        "output_schema": {
            "type": "object",
            "properties": {"result": {"type": "number"}},
        },
        "risk_level": RiskLevel.low,
    },
    {
        "name": "knowledge_search",
        "description": "Search approved knowledge collections.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
        "output_schema": {"type": "object"},
        "risk_level": RiskLevel.low,
    },
    {
        "name": "current_datetime",
        "description": "Return server-controlled date and time.",
        "input_schema": {"type": "object", "properties": {}},
        "output_schema": {
            "type": "object",
            "properties": {"datetime_utc": {"type": "string"}},
        },
        "risk_level": RiskLevel.low,
    },
]

TEMPLATES = [
    {
        "slug": "customer-support",
        "name": "Customer Support Assistant",
        "risk_level": RiskLevel.medium,
        "setup_effort": "medium",
    },
    {
        "slug": "erp-support",
        "name": "ERP Support Assistant",
        "risk_level": RiskLevel.medium,
        "setup_effort": "high",
    },
    {
        "slug": "hr-policy",
        "name": "HR Policy Assistant",
        "risk_level": RiskLevel.high,
        "setup_effort": "high",
    },
    {
        "slug": "document-qa",
        "name": "Document Q&A Assistant",
        "risk_level": RiskLevel.low,
        "setup_effort": "low",
    },
    {
        "slug": "sales-product",
        "name": "Sales Product Assistant",
        "risk_level": RiskLevel.medium,
        "setup_effort": "medium",
    },
    {
        "slug": "developer-docs",
        "name": "Developer Documentation Assistant",
        "risk_level": RiskLevel.low,
        "setup_effort": "medium",
    },
    {
        "slug": "compliance-policy",
        "name": "Compliance and Policy Assistant",
        "risk_level": RiskLevel.high,
        "setup_effort": "high",
    },
    {
        "slug": "general-assistant",
        "name": "General Assistant",
        "risk_level": RiskLevel.low,
        "setup_effort": "low",
    },
    {
        "slug": "empty",
        "name": "Start from Empty",
        "risk_level": RiskLevel.low,
        "setup_effort": "low",
    },
]

DEFAULT_PROMPT = """ROLE
You are a helpful assistant.

PRIMARY OBJECTIVE
Answer questions accurately using approved knowledge only.

WHEN INFORMATION IS MISSING
State that approved knowledge does not contain enough information.
"""


def seed_owner(db: Session) -> None:
    existing = db.query(User).filter(User.email == settings.owner_email).first()
    if existing:
        return
    user = User(
        email=settings.owner_email,
        password_hash=hash_password(settings.owner_password),
        role=UserRole.owner,
        is_active=True,
    )
    db.add(user)


def seed_tools(db: Session) -> None:
    for tool_data in TOOLS:
        if db.query(Tool).filter(Tool.name == tool_data["name"]).first():
            continue
        db.add(Tool(**tool_data))


def seed_templates(db: Session) -> None:
    for tpl in TEMPLATES:
        existing = db.query(AgentTemplate).filter(AgentTemplate.slug == tpl["slug"]).first()
        if existing:
            continue
        template = AgentTemplate(
            slug=tpl["slug"],
            name=tpl["name"],
            description=f"Template for {tpl['name']}.",
            intended_use=f"Use for {tpl['name']} scenarios.",
            not_suitable_for="Not for unverified or high-risk autonomous actions.",
            target_users="Internal users and support staff.",
            risk_level=tpl["risk_level"],
            setup_effort=tpl["setup_effort"],
        )
        db.add(template)
        db.flush()
        version = AgentTemplateVersion(
            template_id=template.id,
            version_number=1,
            system_prompt=DEFAULT_PROMPT.replace("helpful assistant", tpl["name"]),
            model_config_json={"provider": "mock", "model": "mock-model", "temperature": 0.3},
            retrieval_config={"enabled": tpl["slug"] != "empty", "top_k": 5},
            tool_config={"calculator": "auto", "knowledge_search": "auto"},
            memory_config={"mode": "conversation"},
        )
        db.add(version)
        db.flush()
        template.current_version_id = version.id


def run_seed() -> None:
    with SessionLocal() as db:
        seed_owner(db)
        seed_tools(db)
        seed_templates(db)
        db.commit()
    print("Seed completed.")


if __name__ == "__main__":
    run_seed()
