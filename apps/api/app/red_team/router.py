import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.authentication.router import CurrentUser
from app.core.db import get_db
from app.models.entities import (
    Agent,
    AgentVersion,
    AuditLog,
    BackgroundJob,
    CaseSeverity,
    CaseStatus,
    EvaluationCase,
    EvaluationDataset,
    EvaluationDatasetVersion,
    JobStatus,
    RedTeamCase,
    RedTeamRun,
    RedTeamRunStatus,
)
from app.red_team.schemas import (
    PromoteResponse,
    RedTeamCaseResponse,
    RedTeamRunCreate,
    RedTeamRunDetail,
    RedTeamRunEstimate,
)
from app.red_team.service import attack_catalog, estimate_red_team_cost, run_red_team_sync
from app.workers.celery_app import run_red_team_task

router = APIRouter(prefix="/red-team", tags=["red-team"])


def _get_user_version(db: Session, user_id: uuid.UUID, version_id: uuid.UUID) -> AgentVersion:
    version = db.get(AgentVersion, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Agent version not found")
    agent = db.get(Agent, version.agent_id)
    if not agent or agent.user_id != user_id:
        raise HTTPException(status_code=404, detail="Agent version not found")
    return version


@router.post("/runs/estimate", response_model=RedTeamRunEstimate)
def estimate_run(
    body: RedTeamRunCreate, user: CurrentUser, db: Session = Depends(get_db)
) -> RedTeamRunEstimate:
    _get_user_version(db, user.id, body.agent_version_id)
    cats = body.categories or None
    count = len(attack_catalog(cats))
    cost = estimate_red_team_cost(db, body.agent_version_id, cats)
    return RedTeamRunEstimate(estimated_cost=cost, case_count=count)


@router.post("/runs", response_model=RedTeamRunDetail, status_code=status.HTTP_201_CREATED)
def start_red_team_run(
    body: RedTeamRunCreate, user: CurrentUser, db: Session = Depends(get_db)
) -> RedTeamRunDetail:
    if not body.confirm:
        raise HTTPException(status_code=400, detail="Set confirm=true after reviewing cost estimate")
    _get_user_version(db, user.id, body.agent_version_id)
    categories = body.categories or []
    run = RedTeamRun(
        user_id=user.id,
        agent_version_id=body.agent_version_id,
        status=RedTeamRunStatus.pending,
        categories=categories,
        config_snapshot={"categories": categories},
    )
    db.add(run)
    db.flush()

    job = BackgroundJob(
        job_type="run_red_team",
        status=JobStatus.pending,
        payload={"run_id": str(run.id)},
    )
    db.add(job)
    db.add(
        AuditLog(
            user_id=user.id,
            action="red_team.start",
            resource_type="red_team_run",
            resource_id=str(run.id),
            details={"categories": categories},
        )
    )
    db.commit()
    run_red_team_task.delay(str(job.id), str(run.id))
    db.refresh(run)
    return _run_detail(run, [])


@router.get("/runs/{run_id}", response_model=RedTeamRunDetail)
def get_red_team_run(
    run_id: uuid.UUID, user: CurrentUser, db: Session = Depends(get_db)
) -> RedTeamRunDetail:
    run = (
        db.query(RedTeamRun)
        .filter(RedTeamRun.id == run_id, RedTeamRun.user_id == user.id)
        .first()
    )
    if not run:
        raise HTTPException(status_code=404, detail="Red team run not found")
    cases = (
        db.query(RedTeamCase)
        .filter(RedTeamCase.red_team_run_id == run.id)
        .order_by(RedTeamCase.created_at)
        .all()
    )
    return _run_detail(run, cases)


@router.post("/cases/{case_id}/promote", response_model=PromoteResponse)
def promote_red_team_case(
    case_id: uuid.UUID,
    user: CurrentUser,
    db: Session = Depends(get_db),
    dataset_id: uuid.UUID | None = None,
) -> PromoteResponse:
    case = (
        db.query(RedTeamCase)
        .join(RedTeamRun, RedTeamRun.id == RedTeamCase.red_team_run_id)
        .filter(RedTeamCase.id == case_id, RedTeamRun.user_id == user.id)
        .first()
    )
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if case.promoted_case_id:
        return PromoteResponse(
            evaluation_case_id=case.promoted_case_id,
            message="Already promoted",
        )

    if dataset_id:
        dataset = (
            db.query(EvaluationDataset)
            .filter(EvaluationDataset.id == dataset_id, EvaluationDataset.user_id == user.id)
            .first()
        )
    else:
        run = db.get(RedTeamRun, case.red_team_run_id)
        version = db.get(AgentVersion, run.agent_version_id) if run else None
        agent_id = version.agent_id if version else None
        dataset = (
            db.query(EvaluationDataset)
            .filter(EvaluationDataset.user_id == user.id, EvaluationDataset.agent_id == agent_id)
            .order_by(EvaluationDataset.created_at.desc())
            .first()
        )
    if not dataset:
        raise HTTPException(status_code=400, detail="No evaluation dataset to promote into")

    dv = (
        db.query(EvaluationDatasetVersion)
        .filter(EvaluationDatasetVersion.dataset_id == dataset.id)
        .order_by(EvaluationDatasetVersion.version_number.desc())
        .first()
    )
    if not dv:
        raise HTTPException(status_code=400, detail="Dataset has no version")

    eval_case = EvaluationCase(
        dataset_version_id=dv.id,
        name=f"Red team: {case.category}",
        category="security",
        user_message=case.payload,
        expected_behaviour="Refuse or handle safely",
        severity=CaseSeverity.high,
        status=CaseStatus.draft,
        notes=f"Promoted from red team case {case.id}",
    )
    db.add(eval_case)
    db.flush()
    case.promoted_case_id = eval_case.id
    db.commit()
    return PromoteResponse(
        evaluation_case_id=eval_case.id,
        message="Promoted as draft evaluation case",
    )


def _run_detail(run: RedTeamRun, cases: list[RedTeamCase]) -> RedTeamRunDetail:
    return RedTeamRunDetail(
        id=run.id,
        status=run.status.value,
        agent_version_id=run.agent_version_id,
        categories=list(run.categories or []),
        created_at=run.created_at,
        completed_at=run.completed_at,
        cases=[
            RedTeamCaseResponse(
                id=c.id,
                category=c.category,
                payload=c.payload,
                response=c.response,
                passed=c.passed,
                severity=c.severity,
                promoted_case_id=c.promoted_case_id,
            )
            for c in cases
        ],
    )
