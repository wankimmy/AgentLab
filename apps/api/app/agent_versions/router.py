import uuid
from copy import deepcopy

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.agents.router import _get_user_agent
from app.authentication.router import CurrentUser
from app.core.db import get_db
from app.models.entities import AgentVersion, RuntimeType
from app.schemas.common import AgentVersionResponse, VersionCreate

router = APIRouter(prefix="/agents/{agent_id}/versions", tags=["agent-versions"])


@router.get("", response_model=list[AgentVersionResponse])
def list_versions(
    agent_id: uuid.UUID, user: CurrentUser, db: Session = Depends(get_db)
) -> list[AgentVersionResponse]:
    _get_user_agent(agent_id, user, db)
    versions = (
        db.query(AgentVersion)
        .filter(AgentVersion.agent_id == agent_id)
        .order_by(AgentVersion.version_number.desc())
        .all()
    )
    return [AgentVersionResponse.model_validate(v) for v in versions]


@router.get("/{version_id}", response_model=AgentVersionResponse)
def get_version(
    agent_id: uuid.UUID,
    version_id: uuid.UUID,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> AgentVersionResponse:
    version = _get_version(agent_id, version_id, user, db)
    return AgentVersionResponse.model_validate(version)


@router.post("", response_model=AgentVersionResponse, status_code=status.HTTP_201_CREATED)
def create_version(
    agent_id: uuid.UUID,
    body: VersionCreate,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> AgentVersionResponse:
    agent = _get_user_agent(agent_id, user, db)
    latest = (
        db.query(AgentVersion)
        .filter(AgentVersion.agent_id == agent_id)
        .order_by(AgentVersion.version_number.desc())
        .first()
    )
    next_number = (latest.version_number + 1) if latest else 1

    parent: AgentVersion | None = None
    if body.parent_version_id:
        parent = _get_version(agent_id, body.parent_version_id, user, db)
    elif body.copy_from_active and agent.active_version_id:
        parent = db.get(AgentVersion, agent.active_version_id)

    version_data = {
        "system_prompt": body.system_prompt or (parent.system_prompt if parent else ""),
        "provider": body.provider or (parent.provider if parent else "mock"),
        "model": body.model or (parent.model if parent else "mock-model"),
        "runtime_type": (
            body.runtime_type
            if body.runtime_type is not None
            else (parent.runtime_type if parent else RuntimeType.native)
        ),
        "model_config_json": deepcopy(parent.model_config_json) if parent else {"temperature": 0.3},
        "retrieval_config": deepcopy(parent.retrieval_config) if parent else {},
        "tool_config": deepcopy(parent.tool_config) if parent else {},
        "memory_config": deepcopy(parent.memory_config) if parent else {"mode": "conversation"},
        "rag_enabled": parent.rag_enabled if parent else False,
    }
    if body.system_prompt is not None:
        version_data["system_prompt"] = body.system_prompt

    version = AgentVersion(
        agent_id=agent_id,
        version_number=next_number,
        parent_version_id=parent.id if parent else None,
        change_summary=body.change_summary or f"Version {next_number}",
        user_notes=body.user_notes,
        **{k: v for k, v in version_data.items() if v is not None},
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return AgentVersionResponse.model_validate(version)


@router.post("/{version_id}/activate", response_model=AgentVersionResponse)
def activate_version(
    agent_id: uuid.UUID,
    version_id: uuid.UUID,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> AgentVersionResponse:
    agent = _get_user_agent(agent_id, user, db)
    version = _get_version(agent_id, version_id, user, db)
    agent.active_version_id = version.id
    db.commit()
    db.refresh(version)
    return AgentVersionResponse.model_validate(version)


def _get_version(
    agent_id: uuid.UUID, version_id: uuid.UUID, user: CurrentUser, db: Session
) -> AgentVersion:
    _get_user_agent(agent_id, user, db)
    version = (
        db.query(AgentVersion)
        .filter(AgentVersion.id == version_id, AgentVersion.agent_id == agent_id)
        .first()
    )
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    return version
