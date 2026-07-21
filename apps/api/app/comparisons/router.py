import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.authentication.router import CurrentUser
from app.comparisons.schemas import (
    ComparisonCreate,
    ComparisonDetail,
    ComparisonSummary,
    ComparisonSummaryJobResponse,
    ComparisonSummaryRequest,
    comparison_to_detail,
    comparison_to_summary,
)
from app.comparisons.service import create_comparison
from app.comparisons.summary import estimate_summary_cost, summarize_comparison_sync
from app.core.db import get_db
from app.models.entities import ComparisonRun
from app.workers.celery_app import summarize_comparison_task

router = APIRouter(prefix="/comparisons", tags=["comparisons"])


@router.post("", response_model=ComparisonDetail, status_code=status.HTTP_201_CREATED)
def start_comparison(
    body: ComparisonCreate, user: CurrentUser, db: Session = Depends(get_db)
) -> ComparisonDetail:
    try:
        comparison = create_comparison(
            db, user.id, body.baseline_run_id, body.candidate_run_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(comparison)
    return comparison_to_detail(comparison, db)


@router.get("", response_model=list[ComparisonSummary])
def list_comparisons(
    user: CurrentUser, db: Session = Depends(get_db)
) -> list[ComparisonSummary]:
    rows = (
        db.query(ComparisonRun)
        .filter(ComparisonRun.user_id == user.id)
        .order_by(ComparisonRun.created_at.desc())
        .limit(50)
        .all()
    )
    return [comparison_to_summary(c) for c in rows]


@router.get("/{comparison_id}", response_model=ComparisonDetail)
def get_comparison(
    comparison_id: uuid.UUID, user: CurrentUser, db: Session = Depends(get_db)
) -> ComparisonDetail:
    comparison = (
        db.query(ComparisonRun)
        .filter(ComparisonRun.id == comparison_id, ComparisonRun.user_id == user.id)
        .first()
    )
    if not comparison:
        raise HTTPException(status_code=404, detail="Comparison not found")
    return comparison_to_detail(comparison, db)


@router.post("/{comparison_id}/summary", response_model=ComparisonSummaryJobResponse)
def generate_comparison_summary(
    comparison_id: uuid.UUID,
    body: ComparisonSummaryRequest,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> ComparisonSummaryJobResponse:
    if not body.confirm:
        raise HTTPException(status_code=400, detail="Set confirm=true after reviewing cost estimate")
    comparison = (
        db.query(ComparisonRun)
        .filter(ComparisonRun.id == comparison_id, ComparisonRun.user_id == user.id)
        .first()
    )
    if not comparison:
        raise HTTPException(status_code=404, detail="Comparison not found")
    if comparison.status.value != "completed":
        raise HTTPException(status_code=400, detail="Comparison must be completed")

    _ = estimate_summary_cost(comparison)
    summarize_comparison_task.delay(str(comparison.id))
    if not comparison.ai_summary:
        summarize_comparison_sync(db, comparison.id)
        db.commit()
        db.refresh(comparison)
    return ComparisonSummaryJobResponse(
        ai_summary=comparison.ai_summary,
        ai_summary_status=comparison.ai_summary_status or "pending",
    )
