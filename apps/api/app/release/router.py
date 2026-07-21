import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.authentication.router import CurrentUser
from app.core.db import get_db
from app.models.entities import CaseClassification, ComparisonRun, RegressionResult
from app.release.service import mark_release_ready, run_release_check

router = APIRouter(tags=["regressions"])


class RegressionListItem(BaseModel):
    id: uuid.UUID
    comparison_run_id: uuid.UUID
    case_name: str
    classification: str
    severity: str
    details: dict
    created_at: datetime


@router.get("/regressions", response_model=list[RegressionListItem])
def list_regressions(user: CurrentUser, db: Session = Depends(get_db)) -> list[RegressionListItem]:
    rows = (
        db.query(RegressionResult, ComparisonRun)
        .join(ComparisonRun, ComparisonRun.id == RegressionResult.comparison_run_id)
        .filter(
            ComparisonRun.user_id == user.id,
            RegressionResult.classification == CaseClassification.regressed,
        )
        .order_by(RegressionResult.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        RegressionListItem(
            id=r.id,
            comparison_run_id=r.comparison_run_id,
            case_name=r.case_name,
            classification=r.classification.value,
            severity=r.severity,
            details=r.details or {},
            created_at=r.created_at,
        )
        for r, _ in rows
    ]


class ThresholdTemplateResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    rules: dict


@router.get("/release-threshold-templates", response_model=list[ThresholdTemplateResponse])
def list_threshold_templates(
    user: CurrentUser, db: Session = Depends(get_db)
) -> list[ThresholdTemplateResponse]:
    del user
    from app.models.entities import ReleaseThresholdTemplate

    rows = db.query(ReleaseThresholdTemplate).order_by(ReleaseThresholdTemplate.name).all()
    return [
        ThresholdTemplateResponse(
            id=r.id, name=r.name, description=r.description, rules=r.rules or {}
        )
        for r in rows
    ]


class ReleaseCheckBody(BaseModel):
    eval_run_id: uuid.UUID | None = None
    dataset_version_id: uuid.UUID | None = None
    threshold_template_id: uuid.UUID | None = None
    preset_id: str = "release_readiness"


class ReleaseCheckResponse(BaseModel):
    id: uuid.UUID
    status: str
    eval_run_id: uuid.UUID | None
    findings: dict = Field(default_factory=dict)


@router.post(
    "/agents/{agent_id}/versions/{version_id}/release-check",
    response_model=ReleaseCheckResponse,
    status_code=status.HTTP_201_CREATED,
)
def release_check(
    agent_id: uuid.UUID,
    version_id: uuid.UUID,
    body: ReleaseCheckBody,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> ReleaseCheckResponse:
    try:
        check = run_release_check(
            db,
            user_id=user.id,
            agent_id=agent_id,
            version_id=version_id,
            eval_run_id=body.eval_run_id,
            dataset_version_id=body.dataset_version_id,
            threshold_template_id=body.threshold_template_id,
            preset_id=body.preset_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(check)
    return ReleaseCheckResponse(
        id=check.id,
        status=check.status.value,
        eval_run_id=check.eval_run_id,
        findings=check.findings or {},
    )


@router.post("/agents/{agent_id}/versions/{version_id}/mark-release-ready")
def mark_ready(
    agent_id: uuid.UUID,
    version_id: uuid.UUID,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    try:
        version = mark_release_ready(
            db, user_id=user.id, agent_id=agent_id, version_id=version_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return {"release_status": version.release_status.value}
