import uuid
from typing import Any

from pydantic import BaseModel, Field

from app.models.entities import (
    AgentStatus,
    EvaluationStatus,
    ReleaseStatus,
    RiskLevel,
    RuntimeType,
)


class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    purpose: str | None = None
    target_audience: str | None = None
    risk_level: RiskLevel = RiskLevel.low
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None
    template_id: uuid.UUID | None = None
    system_prompt: str = ""
    provider: str = "mock"
    model: str = "mock-model"


class AgentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    purpose: str | None = None
    target_audience: str | None = None
    risk_level: RiskLevel | None = None
    tags: list[str] | None = None
    notes: str | None = None


class AgentVersionResponse(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    version_number: int
    parent_version_id: uuid.UUID | None
    system_prompt: str
    provider: str
    model: str
    runtime_type: RuntimeType
    model_settings: dict[str, Any] = Field(validation_alias="model_config_json")
    retrieval_config: dict[str, Any]
    tool_config: dict[str, Any]
    memory_config: dict[str, Any]
    rag_enabled: bool
    change_summary: str | None
    user_notes: str | None
    evaluation_status: EvaluationStatus
    release_status: ReleaseStatus

    model_config = {"from_attributes": True, "populate_by_name": True}


class AgentResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    purpose: str | None
    target_audience: str | None
    risk_level: RiskLevel
    status: AgentStatus
    tags: list[str] | None
    notes: str | None
    active_version_id: uuid.UUID | None
    template_id: uuid.UUID | None
    active_version: AgentVersionResponse | None = None

    model_config = {"from_attributes": True}


class AgentListResponse(BaseModel):
    items: list[AgentResponse]
    total: int
    page: int
    page_size: int


class VersionCreate(BaseModel):
    parent_version_id: uuid.UUID | None = None
    system_prompt: str | None = None
    provider: str | None = None
    model: str | None = None
    change_summary: str | None = None
    user_notes: str | None = None
    copy_from_active: bool = True


class TemplateSummary(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    description: str
    risk_level: RiskLevel
    setup_effort: str

    model_config = {"from_attributes": True}


class TemplateDetail(TemplateSummary):
    intended_use: str
    not_suitable_for: str
    target_users: str
    system_prompt: str = ""
    model_config_data: dict[str, Any] = Field(default_factory=dict)
    retrieval_config: dict[str, Any] = Field(default_factory=dict)
    tool_config: dict[str, Any] = Field(default_factory=dict)
