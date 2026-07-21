import uuid
from datetime import datetime

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.entities import ComparisonRun, RegressionResult


class ComparisonCreate(BaseModel):
    baseline_run_id: uuid.UUID
    candidate_run_id: uuid.UUID


class CaseDeltaResponse(BaseModel):
    case_id: str | None
    case_name: str
    classification: str
    severity: str
    baseline_pass: bool
    candidate_pass: bool
    details: dict = Field(default_factory=dict)


class ComparisonSummary(BaseModel):
    id: uuid.UUID
    status: str
    baseline_pass_rate: float | None
    candidate_pass_rate: float | None
    pass_rate_delta: float | None
    created_at: datetime
    completed_at: datetime | None
    ai_summary_status: str | None = None


class ComparisonDetail(ComparisonSummary):
    baseline_run_id: uuid.UUID | None
    candidate_run_id: uuid.UUID | None
    baseline_agent_version_id: uuid.UUID
    candidate_agent_version_id: uuid.UUID
    ai_summary: str | None = None
    cases: list[CaseDeltaResponse] = Field(default_factory=list)


class ComparisonSummaryRequest(BaseModel):
    confirm: bool = False


class ComparisonSummaryJobResponse(BaseModel):
    ai_summary: str | None
    ai_summary_status: str


class RegressionListItem(BaseModel):
    id: uuid.UUID
    comparison_run_id: uuid.UUID
    case_name: str
    classification: str
    severity: str
    details: dict
    created_at: datetime


def comparison_to_detail(comparison: ComparisonRun, db: Session) -> ComparisonDetail:
    regressions = (
        db.query(RegressionResult)
        .filter(RegressionResult.comparison_run_id == comparison.id)
        .order_by(RegressionResult.case_name)
        .all()
    )
    cases = [
        CaseDeltaResponse(
            case_id=str(r.case_id) if r.case_id else None,
            case_name=r.case_name,
            classification=r.classification.value,
            severity=r.severity,
            baseline_pass=bool((r.details or {}).get("baseline_pass")),
            candidate_pass=bool((r.details or {}).get("candidate_pass")),
            details=r.details or {},
        )
        for r in regressions
    ]
    return ComparisonDetail(
        id=comparison.id,
        status=comparison.status.value,
        baseline_pass_rate=float(comparison.baseline_pass_rate)
        if comparison.baseline_pass_rate is not None
        else None,
        candidate_pass_rate=float(comparison.candidate_pass_rate)
        if comparison.candidate_pass_rate is not None
        else None,
        pass_rate_delta=float(comparison.pass_rate_delta) if comparison.pass_rate_delta else None,
        created_at=comparison.created_at,
        completed_at=comparison.completed_at,
        ai_summary_status=comparison.ai_summary_status,
        baseline_run_id=comparison.baseline_run_id,
        candidate_run_id=comparison.candidate_run_id,
        baseline_agent_version_id=comparison.baseline_agent_version_id,
        candidate_agent_version_id=comparison.candidate_agent_version_id,
        ai_summary=comparison.ai_summary,
        cases=cases,
    )


def comparison_to_summary(comparison: ComparisonRun) -> ComparisonSummary:
    return ComparisonSummary(
        id=comparison.id,
        status=comparison.status.value,
        baseline_pass_rate=float(comparison.baseline_pass_rate)
        if comparison.baseline_pass_rate is not None
        else None,
        candidate_pass_rate=float(comparison.candidate_pass_rate)
        if comparison.candidate_pass_rate is not None
        else None,
        pass_rate_delta=float(comparison.pass_rate_delta) if comparison.pass_rate_delta else None,
        created_at=comparison.created_at,
        completed_at=comparison.completed_at,
        ai_summary_status=comparison.ai_summary_status,
    )
