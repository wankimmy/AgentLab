"""Seed owner user, tools, templates, guides, sample packs, and model registry."""

from decimal import Decimal
from typing import Any, cast

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models.entities import (
    AgentTemplate,
    AgentTemplateVersion,
    Guide,
    GuideSection,
    GuideSectionContent,
    ModelPricing,
    ModelRegistry,
    RiskLevel,
    SampleDataPack,
    Tool,
    User,
    UserRole,
)
from app.seed_data import GUIDES, template_version_data

TOOLS = [
    {
        "name": "calculator",
        "description": "Evaluate a mathematical expression safely.",
        "input_schema": {
            "type": "object",
            "properties": {"expression": {"type": "string"}},
            "required": ["expression"],
        },
        "output_schema": {"type": "object", "properties": {"result": {"type": "number"}}},
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
        "output_schema": {"type": "object", "properties": {"datetime_utc": {"type": "string"}}},
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


def seed_owner(db: Session) -> None:
    if db.query(User).filter(User.email == settings.owner_email).first():
        return
    db.add(
        User(
            email=settings.owner_email,
            password_hash=hash_password(settings.owner_password),
            role=UserRole.owner,
            is_active=True,
        )
    )


def seed_tools(db: Session) -> None:
    for tool_data in TOOLS:
        if db.query(Tool).filter(Tool.name == tool_data["name"]).first():
            continue
        db.add(Tool(**tool_data))


def _upsert_template_version(db: Session, template: AgentTemplate, tpl: dict) -> None:
    rich = tpl["slug"] == "erp-support"
    data = template_version_data(tpl["slug"], tpl["name"], rich=rich)
    if template.current_version_id:
        tv = db.get(AgentTemplateVersion, template.current_version_id)
        if tv:
            for key, value in data.items():
                setattr(tv, key, value)
            return
    version = AgentTemplateVersion(template_id=template.id, version_number=1, **data)
    db.add(version)
    db.flush()
    template.current_version_id = version.id


def seed_templates(db: Session) -> None:
    for tpl in TEMPLATES:
        template = db.query(AgentTemplate).filter(AgentTemplate.slug == tpl["slug"]).first()
        if not template:
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
        _upsert_template_version(db, template, tpl)


def seed_guides(db: Session) -> None:
    for idx, raw_guide in enumerate(GUIDES):
        guide_data = cast(dict[str, Any], raw_guide)
        guide = db.query(Guide).filter(Guide.slug == guide_data["slug"]).first()
        if not guide:
            guide = Guide(
                slug=guide_data["slug"],
                title=guide_data["title"],
                section=GuideSection(guide_data["section"]),
                summary=guide_data["summary"],
                sort_order=idx,
                screen_link=guide_data.get("screen_link"),
            )
            db.add(guide)
            db.flush()
            for sidx, section in enumerate(
                cast(list[dict[str, Any]], guide_data.get("sections", []))
            ):
                db.add(
                    GuideSectionContent(
                        guide_id=guide.id,
                        heading=section["heading"],
                        content=section["content"],
                        sort_order=sidx,
                    )
                )
        else:
            guide.title = guide_data["title"]
            guide.summary = guide_data["summary"]
            guide.sort_order = idx


def seed_sample_packs(db: Session) -> None:
    pack = db.query(SampleDataPack).filter(SampleDataPack.slug == "erp-support").first()
    if pack:
        return
    db.add(
        SampleDataPack(
            slug="erp-support",
            name="ERP Support Sample Pack",
            description=(
                "Synthetic ERP support agent, knowledge stubs, "
                "and evaluation cases for portfolio demo."
            ),
            is_synthetic=True,
            template_slug="erp-support",
            manifest={
                "label": "SYNTHETIC DATA",
                "includes": ["agent_template", "eval_starter_pack", "security_cases"],
                "knowledge_docs": 7,
                "eval_cases": 25,
            },
        )
    )


MODELS = [
    {
        "provider": "mock",
        "model": "mock-model",
        "context_limit": 8192,
        "streaming": True,
        "tool_calling": False,
        "input_cost": Decimal("0"),
        "output_cost": Decimal("0"),
    },
    {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "context_limit": 128000,
        "streaming": True,
        "tool_calling": True,
        "input_cost": Decimal("0.00000015"),
        "output_cost": Decimal("0.0000006"),
    },
]


def seed_models(db: Session) -> None:
    for entry in MODELS:
        reg = (
            db.query(ModelRegistry)
            .filter(
                ModelRegistry.provider == entry["provider"], ModelRegistry.model == entry["model"]
            )
            .first()
        )
        if not reg:
            reg = ModelRegistry(
                provider=entry["provider"],
                model=entry["model"],
                context_limit=entry["context_limit"],
                streaming=entry["streaming"],
                tool_calling=entry["tool_calling"],
                active=True,
            )
            db.add(reg)
            db.flush()
        pricing = (
            db.query(ModelPricing)
            .filter(
                ModelPricing.provider == entry["provider"],
                ModelPricing.model == entry["model"],
            )
            .first()
        )
        if not pricing:
            db.add(
                ModelPricing(
                    provider=entry["provider"],
                    model=entry["model"],
                    input_token_cost=entry["input_cost"],
                    output_token_cost=entry["output_cost"],
                )
            )


def run_seed() -> None:
    from app.core.db import SessionLocal

    with SessionLocal() as db:
        seed_owner(db)
        seed_tools(db)
        seed_templates(db)
        seed_guides(db)
        seed_sample_packs(db)
        seed_models(db)
        db.commit()
    print("Seed completed.")


if __name__ == "__main__":
    run_seed()
