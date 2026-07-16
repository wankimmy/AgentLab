import uuid
from copy import deepcopy

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.authentication.router import CurrentUser
from app.core.db import get_db
from app.models.entities import (
    Agent,
    AgentStatus,
    AgentVersion,
)
from app.schemas.common import (
    AgentCreate,
    AgentListResponse,
    AgentResponse,
    AgentUpdate,
    AgentVersionResponse,
)
from app.seed_data import DEFAULT_TOOL_CONFIG
from app.services.template_service import version_defaults_from_template

router = APIRouter(prefix="/agents", tags=["agents"])


def _agent_to_response(agent: Agent, db: Session) -> AgentResponse:
    active_version = None
    if agent.active_version_id:
        version = db.get(AgentVersion, agent.active_version_id)
        if version:
            active_version = AgentVersionResponse.model_validate(version)
    return AgentResponse(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        purpose=agent.purpose,
        target_audience=agent.target_audience,
        risk_level=agent.risk_level,
        status=agent.status,
        tags=agent.tags or [],
        notes=agent.notes,
        active_version_id=agent.active_version_id,
        template_id=agent.template_id,
        active_version=active_version,
    )


@router.get("", response_model=AgentListResponse)
def list_agents(
    user: CurrentUser,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: AgentStatus | None = Query(None, alias="status"),
) -> AgentListResponse:
    query = db.query(Agent).filter(Agent.user_id == user.id)
    if status_filter:
        query = query.filter(Agent.status == status_filter)
    total = query.count()
    agents = (
        query.order_by(Agent.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return AgentListResponse(
        items=[_agent_to_response(a, db) for a in agents],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
def create_agent(
    body: AgentCreate,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> AgentResponse:
    version_defaults: dict = {
        "system_prompt": body.system_prompt,
        "provider": body.provider,
        "model": body.model,
        "model_config_json": {"temperature": 0.3, "max_tokens": 1024},
        "retrieval_config": {},
        "tool_config": deepcopy(DEFAULT_TOOL_CONFIG),
        "memory_config": {"mode": "conversation"},
        "rag_enabled": False,
    }
    if body.template_id:
        version_defaults.update(version_defaults_from_template(db, body.template_id))

    agent = Agent(
        user_id=user.id,
        name=body.name,
        description=body.description,
        purpose=body.purpose,
        target_audience=body.target_audience,
        risk_level=body.risk_level,
        tags=body.tags,
        notes=body.notes,
        template_id=body.template_id,
    )
    db.add(agent)
    db.flush()

    version = AgentVersion(
        agent_id=agent.id,
        version_number=1,
        parent_version_id=None,
        change_summary="Initial version",
        **version_defaults,
    )
    db.add(version)
    db.flush()
    agent.active_version_id = version.id
    db.commit()
    db.refresh(agent)
    return _agent_to_response(agent, db)


@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(
    agent_id: uuid.UUID, user: CurrentUser, db: Session = Depends(get_db)
) -> AgentResponse:
    agent = _get_user_agent(agent_id, user, db)
    return _agent_to_response(agent, db)


@router.patch("/{agent_id}", response_model=AgentResponse)
def update_agent(
    agent_id: uuid.UUID,
    body: AgentUpdate,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> AgentResponse:
    agent = _get_user_agent(agent_id, user, db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(agent, field, value)
    db.commit()
    db.refresh(agent)
    return _agent_to_response(agent, db)


@router.post("/{agent_id}/archive", response_model=AgentResponse)
def archive_agent(
    agent_id: uuid.UUID, user: CurrentUser, db: Session = Depends(get_db)
) -> AgentResponse:
    agent = _get_user_agent(agent_id, user, db)
    agent.status = AgentStatus.archived
    db.commit()
    db.refresh(agent)
    return _agent_to_response(agent, db)


@router.post("/{agent_id}/restore", response_model=AgentResponse)
def restore_agent(
    agent_id: uuid.UUID, user: CurrentUser, db: Session = Depends(get_db)
) -> AgentResponse:
    agent = _get_user_agent(agent_id, user, db)
    agent.status = AgentStatus.active
    db.commit()
    db.refresh(agent)
    return _agent_to_response(agent, db)


@router.post("/{agent_id}/clone", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
def clone_agent(
    agent_id: uuid.UUID, user: CurrentUser, db: Session = Depends(get_db)
) -> AgentResponse:
    source = _get_user_agent(agent_id, user, db)
    if not source.active_version_id:
        raise HTTPException(status_code=400, detail="Agent has no active version to clone")
    source_version = db.get(AgentVersion, source.active_version_id)
    if not source_version:
        raise HTTPException(status_code=400, detail="Active version not found")

    clone = Agent(
        user_id=user.id,
        name=f"{source.name} (copy)",
        description=source.description,
        purpose=source.purpose,
        target_audience=source.target_audience,
        risk_level=source.risk_level,
        tags=source.tags,
        notes=source.notes,
        template_id=source.template_id,
    )
    db.add(clone)
    db.flush()

    version = AgentVersion(
        agent_id=clone.id,
        version_number=1,
        parent_version_id=None,
        system_prompt=source_version.system_prompt,
        provider=source_version.provider,
        model=source_version.model,
        runtime_type=source_version.runtime_type,
        model_config_json=deepcopy(source_version.model_config_json),
        retrieval_config=deepcopy(source_version.retrieval_config),
        tool_config=deepcopy(source_version.tool_config),
        memory_config=deepcopy(source_version.memory_config),
        rag_enabled=source_version.rag_enabled,
        change_summary=f"Cloned from agent {source.id}",
    )
    db.add(version)
    db.flush()
    clone.active_version_id = version.id
    db.commit()
    db.refresh(clone)
    return _agent_to_response(clone, db)


def _get_user_agent(agent_id: uuid.UUID, user: CurrentUser, db: Session) -> Agent:
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.user_id == user.id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent
