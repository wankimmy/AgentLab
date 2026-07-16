import uuid
from copy import deepcopy

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.authentication.router import CurrentUser
from app.core.db import get_db
from app.models.entities import Agent, AgentVersion, OnboardingProgress, RiskLevel
from app.schemas.common import (
    DefineDraftRequest,
    DefineDraftResponse,
    OnboardingProgressResponse,
    OnboardingProgressUpdate,
)
from app.services.template_service import create_agent_from_template

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


def _get_or_create_progress(user: CurrentUser, db: Session) -> OnboardingProgress:
    progress = db.get(OnboardingProgress, user.id)
    if not progress:
        progress = OnboardingProgress(
            user_id=user.id, current_step=1, completed=False, step_data={}
        )
        db.add(progress)
        db.flush()
    return progress


@router.get("/progress", response_model=OnboardingProgressResponse)
def get_progress(user: CurrentUser, db: Session = Depends(get_db)) -> OnboardingProgressResponse:
    progress = _get_or_create_progress(user, db)
    db.commit()
    return OnboardingProgressResponse(
        current_step=progress.current_step,
        completed=progress.completed,
        step_data=progress.step_data or {},
    )


@router.put("/progress", response_model=OnboardingProgressResponse)
def update_progress(
    body: OnboardingProgressUpdate,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> OnboardingProgressResponse:
    progress = _get_or_create_progress(user, db)
    progress.current_step = body.current_step
    progress.step_data = {**(progress.step_data or {}), **body.step_data}
    db.commit()
    db.refresh(progress)
    return OnboardingProgressResponse(
        current_step=progress.current_step,
        completed=progress.completed,
        step_data=progress.step_data or {},
    )


@router.post("/define-draft", response_model=DefineDraftResponse)
def define_draft(body: DefineDraftRequest) -> DefineDraftResponse:
    purpose_words = body.purpose.strip().split()
    name_hint = " ".join(purpose_words[:4]).title() if purpose_words else "My Agent"
    suggested_name = f"{name_hint} Assistant"
    questions_note = ""
    if body.example_questions:
        questions_note = f"\nExample questions: {', '.join(body.example_questions[:3])}"
    draft_notes = (
        f"Purpose: {body.purpose}\n"
        f"Audience: {body.target_audience}\n"
        f"Risk level: {body.risk_level.value}"
        f"{questions_note}"
    )
    return DefineDraftResponse(
        suggested_name=suggested_name,
        suggested_purpose=body.purpose.strip(),
        suggested_target_audience=body.target_audience.strip(),
        draft_notes=draft_notes,
    )


@router.post("/complete", response_model=OnboardingProgressResponse)
def complete_onboarding(
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> OnboardingProgressResponse:
    progress = _get_or_create_progress(user, db)
    step_data = progress.step_data or {}
    define = step_data.get("define", {})
    template_step = step_data.get("template", {})
    behaviour = step_data.get("behaviour", {})
    tools = step_data.get("tools", {})

    existing_agent_id = step_data.get("agent_id")
    agent: Agent | None = None
    if existing_agent_id:
        agent = (
            db.query(Agent)
            .filter(Agent.id == uuid.UUID(str(existing_agent_id)), Agent.user_id == user.id)
            .first()
        )

    if not agent:
        template_id_raw = template_step.get("template_id")
        template_id = uuid.UUID(str(template_id_raw)) if template_id_raw else None
        tool_config_override = tools.get("tool_config") if tools else None
        system_prompt_override = behaviour.get("system_prompt") if behaviour else None
        if template_id:
            agent = create_agent_from_template(
                db,
                user,
                template_id,
                name=define.get("name") or define.get("suggested_name"),
                purpose=define.get("purpose") or define.get("suggested_purpose"),
                target_audience=define.get("target_audience")
                or define.get("suggested_target_audience"),
                notes=define.get("draft_notes"),
                system_prompt_override=system_prompt_override,
                tool_config_override=tool_config_override,
            )
        else:
            risk_raw = define.get("risk_level", "medium")
            risk = RiskLevel(risk_raw) if isinstance(risk_raw, str) else RiskLevel.medium
            agent = Agent(
                user_id=user.id,
                name=define.get("name") or define.get("suggested_name") or "My Agent",
                purpose=define.get("purpose") or define.get("suggested_purpose"),
                target_audience=define.get("target_audience")
                or define.get("suggested_target_audience"),
                notes=define.get("draft_notes"),
                risk_level=risk,
            )
            db.add(agent)
            db.flush()
            version = AgentVersion(
                agent_id=agent.id,
                version_number=1,
                parent_version_id=None,
                system_prompt=behaviour.get("system_prompt", ""),
                provider="mock",
                model="mock-model",
                model_config_json={"temperature": 0.3, "max_tokens": 1024},
                retrieval_config={},
                tool_config=deepcopy(tool_config_override or {}),
                memory_config={"mode": "conversation"},
                rag_enabled=False,
                change_summary="Created from onboarding",
            )
            db.add(version)
            db.flush()
            agent.active_version_id = version.id
            db.flush()

    if agent and agent.active_version_id:
        av = db.get(AgentVersion, agent.active_version_id)
        if av:
            if behaviour.get("system_prompt"):
                av.system_prompt = behaviour["system_prompt"]
            if tools.get("tool_config"):
                av.tool_config = deepcopy(tools["tool_config"])
            db.flush()

    step_data["agent_id"] = str(agent.id) if agent else None
    progress.step_data = step_data
    progress.completed = True
    progress.current_step = 8
    db.commit()
    db.refresh(progress)
    return OnboardingProgressResponse(
        current_step=progress.current_step,
        completed=progress.completed,
        step_data=progress.step_data or {},
    )
