import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.authentication.router import CurrentUser
from app.core.db import get_db
from app.models.entities import AgentTemplate, AgentTemplateVersion
from app.schemas.common import AgentResponse, TemplateApplyRequest, TemplateDetail, TemplateSummary
from app.services.template_service import create_agent_from_template

router = APIRouter(prefix="/templates", tags=["templates"])


def _template_detail(template: AgentTemplate, db: Session) -> TemplateDetail:
    tv: AgentTemplateVersion | None = None
    if template.current_version_id:
        tv = db.get(AgentTemplateVersion, template.current_version_id)
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
        system_prompt=tv.system_prompt if tv else "",
        model_config_data=tv.model_config_json if tv else {},
        retrieval_config=tv.retrieval_config if tv else {},
        tool_config=tv.tool_config if tv else {},
        example_questions=tv.example_questions if tv else [],
        example_answers=tv.example_answers if tv else [],
        eval_starter_pack=tv.eval_starter_pack if tv else {},
        judge_rubric=tv.judge_rubric if tv else {},
        security_test_cases=tv.security_test_cases if tv else [],
        release_thresholds=tv.release_thresholds if tv else {},
        common_mistakes=tv.common_mistakes if tv else [],
        deployment_checklist=tv.deployment_checklist if tv else [],
    )


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
    return _template_detail(template, db)


@router.post(
    "/{template_id}/apply", response_model=AgentResponse, status_code=status.HTTP_201_CREATED
)
def apply_template(
    template_id: uuid.UUID,
    body: TemplateApplyRequest,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> AgentResponse:
    from app.agents.router import _agent_to_response

    agent = create_agent_from_template(
        db,
        user,
        template_id,
        name=body.name,
        purpose=body.purpose,
        target_audience=body.target_audience,
        notes=body.notes,
    )
    return _agent_to_response(agent, db)
