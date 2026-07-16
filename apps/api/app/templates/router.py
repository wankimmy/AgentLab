import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.authentication.router import CurrentUser
from app.core.db import get_db
from app.models.entities import AgentTemplate, AgentTemplateVersion
from app.schemas.common import TemplateDetail, TemplateSummary

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("", response_model=list[TemplateSummary])
def list_templates(user: CurrentUser, db: Session = Depends(get_db)) -> list[TemplateSummary]:
    templates = db.query(AgentTemplate).order_by(AgentTemplate.name).all()
    return [TemplateSummary.model_validate(t) for t in templates]


@router.get("/{template_id}", response_model=TemplateDetail)
def get_template(
    template_id: uuid.UUID, user: CurrentUser, db: Session = Depends(get_db)
) -> TemplateDetail:
    template = db.get(AgentTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    system_prompt = ""
    model_config_data: dict = {}
    retrieval_config: dict = {}
    tool_config: dict = {}
    if template.current_version_id:
        tv = db.get(AgentTemplateVersion, template.current_version_id)
        if tv:
            system_prompt = tv.system_prompt
            model_config_data = tv.model_config_json
            retrieval_config = tv.retrieval_config
            tool_config = tv.tool_config
    return TemplateDetail(
        id=template.id,
        slug=template.slug,
        name=template.name,
        description=template.description,
        risk_level=template.risk_level,
        setup_effort=template.setup_effort,
        intended_use=template.intended_use,
        not_suitable_for=template.not_suitable_for,
        target_users=template.target_users,
        system_prompt=system_prompt,
        model_config_data=model_config_data,
        retrieval_config=retrieval_config,
        tool_config=tool_config,
    )
