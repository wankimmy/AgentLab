import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.models.entities import CaseSeverity, CaseStatus, EvalMode, ResultStatus, RunStatus


class EvalTemplateResponse(BaseModel):
    id: str
    name: str
    description: str
    metrics: list[str]
    quick_metrics: list[str]
    thresholds: dict[str, float]


class DatasetCreate(BaseModel):
    name: str
    description: str = ""
    agent_id: uuid.UUID | None = None
    template_id: uuid.UUID | None = None


class DatasetSummary(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    agent_id: uuid.UUID | None
    template_id: uuid.UUID | None
    latest_version: int | None
    case_count: int = 0
    created_at: datetime
    updated_at: datetime


class DatasetDetail(DatasetSummary):
    versions: list["VersionSummary"] = Field(default_factory=list)


class VersionCreate(BaseModel):
    copy_previous: bool = True


class VersionSummary(BaseModel):
    id: uuid.UUID
    version_number: int
    case_count: int
    created_at: datetime


class CaseCreate(BaseModel):
    name: str
    category: str = ""
    user_message: str
    conversation_history: dict | list | None = None
    expected_answer: str | None = None
    expected_behaviour: str | None = None
    required_keywords: list[str] = Field(default_factory=list)
    forbidden_keywords: list[str] = Field(default_factory=list)
    forbidden_claims: list[str] = Field(default_factory=list)
    expected_source: str | None = None
    expected_citation: str | None = None
    expected_tool: str | None = None
    expected_tool_args: dict | None = None
    max_latency_ms: int | None = None
    max_tokens: int | None = None
    max_cost: Decimal | None = None
    severity: CaseSeverity = CaseSeverity.medium
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None
    requires_human_review: bool = False
    status: CaseStatus = CaseStatus.approved


class CaseUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    user_message: str | None = None
    expected_answer: str | None = None
    expected_behaviour: str | None = None
    required_keywords: list[str] | None = None
    forbidden_keywords: list[str] | None = None
    forbidden_claims: list[str] | None = None
    expected_source: str | None = None
    expected_citation: str | None = None
    expected_tool: str | None = None
    expected_tool_args: dict | None = None
    max_latency_ms: int | None = None
    max_tokens: int | None = None
    severity: CaseSeverity | None = None
    status: CaseStatus | None = None


class CaseResponse(CaseCreate):
    id: uuid.UUID


class VersionDetail(VersionSummary):
    cases: list[CaseResponse] = Field(default_factory=list)


class RunEstimateRequest(BaseModel):
    agent_version_id: uuid.UUID
    dataset_version_id: uuid.UUID
    mode: EvalMode = EvalMode.quick
    preset_id: str = "customer_support_quality"
    include_semantic: bool = True


class RunEstimateResponse(BaseModel):
    estimated_cost: float
    case_count: int
    mode: EvalMode
    warnings: list[str] = Field(default_factory=list)


class RunCreate(RunEstimateRequest):
    pass


class MetricResultResponse(BaseModel):
    metric_name: str
    metric_type: str
    passed: bool
    score: float | None
    threshold: float | None
    details: dict[str, Any] = Field(default_factory=dict)


class ResultResponse(BaseModel):
    id: uuid.UUID
    case_id: uuid.UUID
    case_name: str
    status: ResultStatus
    actual_answer: str
    overall_pass: bool
    failure_explanation: str | None
    latency_ms: int
    tokens: int
    cost: float
    metrics: list[MetricResultResponse] = Field(default_factory=list)


class RunSummary(BaseModel):
    id: uuid.UUID
    agent_version_id: uuid.UUID
    dataset_version_id: uuid.UUID
    mode: EvalMode
    status: RunStatus
    pass_rate: float | None
    total_cost: float | None
    progress: dict[str, int] = Field(default_factory=dict)
    started_at: datetime
    completed_at: datetime | None


class RunDetail(RunSummary):
    config_snapshot: dict[str, Any] = Field(default_factory=dict)
    results: list[ResultResponse] = Field(default_factory=list)
