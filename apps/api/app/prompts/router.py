import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agent_versions.router import _get_version
from app.authentication.router import CurrentUser
from app.core.db import get_db
from app.models.entities import (
    BackgroundJob,
    JobStatus,
    PromptRecommendation,
    PromptRecommendationSource,
    PromptRecommendationStatus,
)
from app.prompts.analyser import estimate_analyse_cost, structural_suggestions
from app.workers.celery_app import analyse_prompt_task

router = APIRouter(tags=["prompts"])


class AnalyseRequest(BaseModel):
    source: str = "analyse"
    confirm: bool = False


class AnalyseEstimate(BaseModel):
    estimated_cost: float
    structural_issues: int


class RecommendationResponse(BaseModel):
    id: uuid.UUID
    source: str
    status: str
    suggestions: list[dict] = Field(default_factory=list)
    estimated_cost: float | None = None


@router.get(
    "/agents/{agent_id}/versions/{version_id}/prompt/completeness",
)
def prompt_completeness(
    agent_id: uuid.UUID,
    version_id: uuid.UUID,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> dict:
    version = _get_version(agent_id, version_id, user, db)
    missing = structural_suggestions(version.system_prompt or "")
    score = max(0, min(100, 100 - len(missing) * 15))
    return {"score": score, "missing": missing}


@router.post(
    "/agents/{agent_id}/versions/{version_id}/prompt/analyse/estimate",
    response_model=AnalyseEstimate,
)
def analyse_estimate(
    agent_id: uuid.UUID,
    version_id: uuid.UUID,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> AnalyseEstimate:
    version = _get_version(agent_id, version_id, user, db)
    issues = structural_suggestions(version.system_prompt or "")
    return AnalyseEstimate(
        estimated_cost=estimate_analyse_cost(version),
        structural_issues=len(issues),
    )


@router.post(
    "/agents/{agent_id}/versions/{version_id}/prompt/analyse",
    response_model=RecommendationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def analyse_prompt(
    agent_id: uuid.UUID,
    version_id: uuid.UUID,
    body: AnalyseRequest,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> RecommendationResponse:
    if not body.confirm:
        raise HTTPException(status_code=400, detail="Set confirm=true after reviewing estimate")
    _get_version(agent_id, version_id, user, db)
    try:
        source = PromptRecommendationSource(body.source)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid source") from exc

    job = BackgroundJob(
        job_type="analyse_prompt",
        status=JobStatus.pending,
        payload={
            "agent_version_id": str(version_id),
            "source": source.value,
            "user_id": str(user.id),
        },
    )
    db.add(job)
    db.commit()
    analyse_prompt_task.delay(str(job.id))
    db.refresh(job)
    rec = (
        db.query(PromptRecommendation)
        .filter(PromptRecommendation.agent_version_id == version_id)
        .order_by(PromptRecommendation.created_at.desc())
        .first()
    )
    if not rec:
        raise HTTPException(status_code=500, detail="Analysis did not produce recommendations")
    return _rec_response(rec)


@router.get(
    "/agents/{agent_id}/versions/{version_id}/prompt/recommendations",
    response_model=list[RecommendationResponse],
)
def list_recommendations(
    agent_id: uuid.UUID,
    version_id: uuid.UUID,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> list[RecommendationResponse]:
    _get_version(agent_id, version_id, user, db)
    rows = (
        db.query(PromptRecommendation)
        .filter(
            PromptRecommendation.agent_version_id == version_id,
            PromptRecommendation.status != PromptRecommendationStatus.dismissed,
        )
        .order_by(PromptRecommendation.created_at.desc())
        .limit(20)
        .all()
    )
    return [_rec_response(r) for r in rows]


@router.post(
    "/agents/{agent_id}/versions/{version_id}/prompt/recommendations/{rec_id}/accept",
    response_model=RecommendationResponse,
)
def accept_recommendation(
    agent_id: uuid.UUID,
    version_id: uuid.UUID,
    rec_id: uuid.UUID,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> RecommendationResponse:
    _get_version(agent_id, version_id, user, db)
    rec = db.get(PromptRecommendation, rec_id)
    if not rec or rec.agent_version_id != version_id:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    rec.status = PromptRecommendationStatus.accepted
    db.commit()
    db.refresh(rec)
    return _rec_response(rec)


@router.post(
    "/agents/{agent_id}/versions/{version_id}/prompt/recommendations/{rec_id}/dismiss",
    response_model=RecommendationResponse,
)
def dismiss_recommendation(
    agent_id: uuid.UUID,
    version_id: uuid.UUID,
    rec_id: uuid.UUID,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> RecommendationResponse:
    _get_version(agent_id, version_id, user, db)
    rec = db.get(PromptRecommendation, rec_id)
    if not rec or rec.agent_version_id != version_id:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    rec.status = PromptRecommendationStatus.dismissed
    db.commit()
    db.refresh(rec)
    return _rec_response(rec)


def _rec_response(rec: PromptRecommendation) -> RecommendationResponse:
    return RecommendationResponse(
        id=rec.id,
        source=rec.source.value,
        status=rec.status.value,
        suggestions=list(rec.suggestions or []),
        estimated_cost=float(rec.estimated_cost) if rec.estimated_cost is not None else None,
    )
