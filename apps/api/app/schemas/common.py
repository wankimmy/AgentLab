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
    example_questions: list[str] = Field(default_factory=list)
    example_answers: list[str] = Field(default_factory=list)
    eval_starter_pack: dict[str, Any] = Field(default_factory=dict)
    judge_rubric: dict[str, Any] = Field(default_factory=dict)
    security_test_cases: list[Any] = Field(default_factory=list)
    release_thresholds: dict[str, Any] = Field(default_factory=dict)
    common_mistakes: list[str] = Field(default_factory=list)
    deployment_checklist: list[str] = Field(default_factory=list)


class TemplateApplyRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    purpose: str | None = None
    target_audience: str | None = None
    notes: str | None = None


class OnboardingProgressResponse(BaseModel):
    current_step: int
    completed: bool
    step_data: dict[str, Any] = Field(default_factory=dict)


class OnboardingProgressUpdate(BaseModel):
    current_step: int = Field(ge=1, le=8)
    step_data: dict[str, Any] = Field(default_factory=dict)


class DefineDraftRequest(BaseModel):
    purpose: str
    target_audience: str
    example_questions: list[str] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.medium


class DefineDraftResponse(BaseModel):
    suggested_name: str
    suggested_purpose: str
    suggested_target_audience: str
    draft_notes: str


class GuideSummary(BaseModel):
    id: uuid.UUID
    slug: str
    title: str
    section: str
    summary: str
    screen_link: str | None = None

    model_config = {"from_attributes": True}


class GuideSectionItem(BaseModel):
    heading: str
    content: str


class GuideDetail(GuideSummary):
    sections: list[GuideSectionItem] = Field(default_factory=list)


class SamplePackSummary(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    description: str
    is_synthetic: bool
    template_slug: str | None = None
    manifest: dict[str, Any] = Field(default_factory=dict)

    model_config = {"from_attributes": True}


class SamplePackInstallResponse(BaseModel):
    agent_id: uuid.UUID
    message: str


class DashboardResponse(BaseModel):
    total_agents: int
    active_versions: int
    draft_versions: int
    onboarding_complete: bool
    latest_pass_rate: float | None = None
    latest_release_status: str | None = None
    recent_regressions: int = 0
    recent_failed_cases: int = 0
    avg_latency_ms: int | None = None
    p95_latency_ms: int | None = None
    recent_token_usage: int = 0
    estimated_cost: float = 0.0
    knowledge_status: str = "not_started"
    background_jobs_pending: int = 0
