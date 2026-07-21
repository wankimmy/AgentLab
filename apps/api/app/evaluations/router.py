import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.authentication.router import CurrentUser
from app.core.db import get_db
from app.evaluations.judge_policy import resolve_judge_enabled
from app.evaluations.import_export import (
    export_cases_csv,
    export_cases_json,
    parse_cases_csv,
    parse_cases_json,
)
from app.evaluations.presets import EVAL_PRESETS, get_preset
from app.evaluations.runner import estimate_evaluation
from app.evaluations.schemas import (
    CaseCreate,
    CaseResponse,
    CaseUpdate,
    DatasetCreate,
    DatasetDetail,
    DatasetSummary,
    EvalTemplateResponse,
    HumanReviewCreate,
    HumanReviewResponse,
    MetricResultResponse,
    ResultResponse,
    RunCreate,
    RunDetail,
    RunEstimateRequest,
    RunEstimateResponse,
    RunSummary,
    VersionCreate,
    VersionDetail,
    VersionSummary,
    GenerateCasesEstimateRequest,
    GenerateCasesEstimateResponse,
    GenerateCasesRequest,
    GenerateCasesResponse,
)
from app.evaluations.case_generation import estimate_generate_cost
from app.models.entities import (
    Agent,
    AgentTemplate,
    AgentTemplateVersion,
    AgentVersion,
    BackgroundJob,
    CaseStatus,
    EvaluationCase,
    EvaluationDataset,
    EvaluationDatasetVersion,
    EvaluationResult,
    EvaluationRun,
    HumanReview,
    HumanReviewVerdict,
    JobStatus,
    JudgeResult,
    MetricResult,
    RunStatus,
)
from app.workers.celery_app import generate_eval_cases_task, run_evaluation_task

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


def _verdict_to_api(verdict: HumanReviewVerdict) -> str:
    if verdict == HumanReviewVerdict.pass_:
        return "pass"
    return verdict.value


def _verdict_from_api(value: str) -> HumanReviewVerdict:
    if value == "pass":
        return HumanReviewVerdict.pass_
    try:
        return HumanReviewVerdict(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid verdict") from exc


def _human_review_response(review: HumanReview) -> HumanReviewResponse:
    return HumanReviewResponse(
        verdict=_verdict_to_api(review.verdict),
        rating=review.rating,
        notes=review.notes,
        issue_category=review.issue_category,
        suggested_improvement=review.suggested_improvement,
        preferred_answer=review.preferred_answer,
    )


def _get_user_dataset(dataset_id: uuid.UUID, user: CurrentUser, db: Session) -> EvaluationDataset:
    dataset = (
        db.query(EvaluationDataset)
        .filter(EvaluationDataset.id == dataset_id, EvaluationDataset.user_id == user.id)
        .first()
    )
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


def _latest_version(db: Session, dataset_id: uuid.UUID) -> EvaluationDatasetVersion | None:
    return (
        db.query(EvaluationDatasetVersion)
        .filter(EvaluationDatasetVersion.dataset_id == dataset_id)
        .order_by(EvaluationDatasetVersion.version_number.desc())
        .first()
    )


def _dataset_summary(db: Session, dataset: EvaluationDataset) -> DatasetSummary:
    latest = _latest_version(db, dataset.id)
    case_count = 0
    if latest:
        case_count = (
            db.query(EvaluationCase).filter(EvaluationCase.dataset_version_id == latest.id).count()
        )
    return DatasetSummary(
        id=dataset.id,
        name=dataset.name,
        description=dataset.description,
        agent_id=dataset.agent_id,
        template_id=dataset.template_id,
        latest_version=latest.version_number if latest else None,
        case_count=case_count,
        created_at=dataset.created_at,
        updated_at=dataset.updated_at,
    )


def _case_response(case: EvaluationCase) -> CaseResponse:
    return CaseResponse(
        id=case.id,
        name=case.name,
        category=case.category,
        user_message=case.user_message,
        conversation_history=case.conversation_history,
        expected_answer=case.expected_answer,
        expected_behaviour=case.expected_behaviour,
        required_keywords=list(case.required_keywords or []),
        forbidden_keywords=list(case.forbidden_keywords or []),
        forbidden_claims=list(case.forbidden_claims or []),
        expected_source=case.expected_source,
        expected_citation=case.expected_citation,
        expected_tool=case.expected_tool,
        expected_tool_args=case.expected_tool_args,
        max_latency_ms=case.max_latency_ms,
        max_tokens=case.max_tokens,
        max_cost=case.max_cost,
        severity=case.severity,
        tags=list(case.tags or []),
        notes=case.notes,
        requires_human_review=case.requires_human_review,
        status=case.status,
    )


def _apply_case_fields(case: EvaluationCase, payload: CaseCreate | CaseUpdate) -> None:
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(case, key, value)


def _user_run(db: Session, run_id: uuid.UUID, user_id: uuid.UUID) -> EvaluationRun:
    run = (
        db.query(EvaluationRun)
        .join(AgentVersion, AgentVersion.id == EvaluationRun.agent_version_id)
        .join(Agent, Agent.id == AgentVersion.agent_id)
        .filter(EvaluationRun.id == run_id, Agent.user_id == user_id)
        .first()
    )
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/templates", response_model=list[EvalTemplateResponse])
def list_eval_templates() -> list[EvalTemplateResponse]:
    return [
        EvalTemplateResponse(
            id=p["id"],
            name=p["name"],
            description=p["description"],
            metrics=p["metrics"],
            quick_metrics=p.get("quick_metrics", []),
            thresholds=p.get("thresholds", {}),
        )
        for p in EVAL_PRESETS
    ]


@router.get("/datasets", response_model=list[DatasetSummary])
def list_datasets(user: CurrentUser, db: Session = Depends(get_db)) -> list[DatasetSummary]:
    datasets = (
        db.query(EvaluationDataset)
        .filter(EvaluationDataset.user_id == user.id)
        .order_by(EvaluationDataset.updated_at.desc())
        .all()
    )
    return [_dataset_summary(db, d) for d in datasets]


@router.post("/datasets", response_model=DatasetSummary, status_code=status.HTTP_201_CREATED)
def create_dataset(
    body: DatasetCreate, user: CurrentUser, db: Session = Depends(get_db)
) -> DatasetSummary:
    dataset = EvaluationDataset(
        user_id=user.id,
        name=body.name,
        description=body.description,
        agent_id=body.agent_id,
        template_id=body.template_id,
    )
    db.add(dataset)
    db.flush()
    version = EvaluationDatasetVersion(dataset_id=dataset.id, version_number=1)
    db.add(version)
    db.commit()
    db.refresh(dataset)
    return _dataset_summary(db, dataset)


@router.post(
    "/datasets/from-template/{template_id}",
    response_model=DatasetSummary,
    status_code=status.HTTP_201_CREATED,
)
def create_dataset_from_template(
    template_id: uuid.UUID, user: CurrentUser, db: Session = Depends(get_db)
) -> DatasetSummary:
    template = db.get(AgentTemplate, template_id)
    if not template or not template.current_version_id:
        raise HTTPException(status_code=404, detail="Template not found")
    tv = db.get(AgentTemplateVersion, template.current_version_id)
    if not tv:
        raise HTTPException(status_code=404, detail="Template version not found")

    pack = tv.eval_starter_pack or {}
    cases_data = pack.get("cases", [])

    dataset = EvaluationDataset(
        user_id=user.id,
        name=f"{template.name} eval pack",
        description=f"Starter evaluation cases from {template.name}",
        template_id=template.id,
    )
    db.add(dataset)
    db.flush()
    version = EvaluationDatasetVersion(dataset_id=dataset.id, version_number=1)
    db.add(version)
    db.flush()

    for row in cases_data:
        case = EvaluationCase(
            dataset_version_id=version.id,
            name=row.get("name", "Case"),
            category=row.get("category", ""),
            user_message=row.get("user_message", ""),
            expected_answer=row.get("expected_answer"),
            expected_behaviour=row.get("expected_behaviour"),
            required_keywords=row.get("required_keywords", []),
            forbidden_keywords=row.get("forbidden_keywords", []),
            forbidden_claims=row.get("forbidden_claims", []),
            expected_source=row.get("expected_source"),
            expected_citation=row.get("expected_citation"),
            expected_tool=row.get("expected_tool"),
            expected_tool_args=row.get("expected_tool_args"),
            severity=row.get("severity", "medium"),
            status=CaseStatus.approved,
        )
        db.add(case)

    db.commit()
    db.refresh(dataset)
    return _dataset_summary(db, dataset)


@router.get("/datasets/{dataset_id}", response_model=DatasetDetail)
def get_dataset(
    dataset_id: uuid.UUID, user: CurrentUser, db: Session = Depends(get_db)
) -> DatasetDetail:
    dataset = _get_user_dataset(dataset_id, user, db)
    summary = _dataset_summary(db, dataset)
    versions = (
        db.query(EvaluationDatasetVersion)
        .filter(EvaluationDatasetVersion.dataset_id == dataset.id)
        .order_by(EvaluationDatasetVersion.version_number.desc())
        .all()
    )
    version_rows: list[VersionSummary] = []
    for v in versions:
        count = db.query(EvaluationCase).filter(EvaluationCase.dataset_version_id == v.id).count()
        version_rows.append(
            VersionSummary(
                id=v.id,
                version_number=v.version_number,
                case_count=count,
                created_at=v.created_at,
            )
        )
    return DatasetDetail(**summary.model_dump(), versions=version_rows)


@router.post(
    "/datasets/{dataset_id}/generate/estimate",
    response_model=GenerateCasesEstimateResponse,
)
def estimate_generate_cases(
    dataset_id: uuid.UUID,
    body: GenerateCasesEstimateRequest,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> GenerateCasesEstimateResponse:
    _get_user_dataset(dataset_id, user, db)
    version = db.get(AgentVersion, body.agent_version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Agent version not found")
    agent = db.get(Agent, version.agent_id)
    if not agent or agent.user_id != user.id:
        raise HTTPException(status_code=404, detail="Agent version not found")
    specs_count = 6
    return GenerateCasesEstimateResponse(
        estimated_cost=estimate_generate_cost(db, version, specs_count),
        draft_count=specs_count,
    )


@router.post(
    "/datasets/{dataset_id}/generate",
    response_model=GenerateCasesResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def generate_draft_cases(
    dataset_id: uuid.UUID,
    body: GenerateCasesRequest,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> GenerateCasesResponse:
    if not body.confirm:
        raise HTTPException(status_code=400, detail="Set confirm=true after reviewing estimate")
    _get_user_dataset(dataset_id, user, db)
    version = db.get(AgentVersion, body.agent_version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Agent version not found")
    agent = db.get(Agent, version.agent_id)
    if not agent or agent.user_id != user.id:
        raise HTTPException(status_code=404, detail="Agent version not found")

    if body.dataset_version_id:
        dv = db.get(EvaluationDatasetVersion, body.dataset_version_id)
        if not dv or dv.dataset_id != dataset_id:
            raise HTTPException(status_code=404, detail="Dataset version not found")
    else:
        dv = _latest_version(db, dataset_id)
    if not dv:
        raise HTTPException(status_code=400, detail="Dataset has no version")

    job = BackgroundJob(
        job_type="generate_eval_cases",
        status=JobStatus.pending,
        payload={
            "dataset_version_id": str(dv.id),
            "agent_version_id": str(version.id),
        },
    )
    db.add(job)
    db.commit()
    generate_eval_cases_task.delay(str(job.id))
    db.refresh(job)
    created_raw = (job.payload or {}).get("created_case_ids", [])
    created_ids = [uuid.UUID(str(x)) for x in created_raw]
    return GenerateCasesResponse(
        job_id=job.id,
        created_case_ids=created_ids,
        message="Draft cases created; approve before using in release runs.",
    )


@router.post(
    "/datasets/{dataset_id}/versions",
    response_model=VersionSummary,
    status_code=status.HTTP_201_CREATED,
)
def create_version(
    dataset_id: uuid.UUID,
    body: VersionCreate,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> VersionSummary:
    dataset = _get_user_dataset(dataset_id, user, db)
    latest = _latest_version(db, dataset.id)
    next_num = (latest.version_number + 1) if latest else 1
    version = EvaluationDatasetVersion(dataset_id=dataset.id, version_number=next_num)
    db.add(version)
    db.flush()

    if body.copy_previous and latest:
        prior_cases = (
            db.query(EvaluationCase).filter(EvaluationCase.dataset_version_id == latest.id).all()
        )
        for old in prior_cases:
            db.add(
                EvaluationCase(
                    dataset_version_id=version.id,
                    name=old.name,
                    category=old.category,
                    user_message=old.user_message,
                    conversation_history=old.conversation_history,
                    expected_answer=old.expected_answer,
                    expected_behaviour=old.expected_behaviour,
                    required_keywords=list(old.required_keywords or []),
                    forbidden_keywords=list(old.forbidden_keywords or []),
                    forbidden_claims=list(old.forbidden_claims or []),
                    expected_source=old.expected_source,
                    expected_citation=old.expected_citation,
                    expected_tool=old.expected_tool,
                    expected_tool_args=old.expected_tool_args,
                    max_latency_ms=old.max_latency_ms,
                    max_tokens=old.max_tokens,
                    max_cost=old.max_cost,
                    severity=old.severity,
                    tags=list(old.tags or []),
                    notes=old.notes,
                    requires_human_review=old.requires_human_review,
                    status=old.status,
                )
            )

    db.commit()
    count = db.query(EvaluationCase).filter(EvaluationCase.dataset_version_id == version.id).count()
    return VersionSummary(
        id=version.id,
        version_number=version.version_number,
        case_count=count,
        created_at=version.created_at,
    )


@router.get("/datasets/{dataset_id}/versions/{version_id}", response_model=VersionDetail)
def get_version(
    dataset_id: uuid.UUID,
    version_id: uuid.UUID,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> VersionDetail:
    _get_user_dataset(dataset_id, user, db)
    version = (
        db.query(EvaluationDatasetVersion)
        .filter(
            EvaluationDatasetVersion.id == version_id,
            EvaluationDatasetVersion.dataset_id == dataset_id,
        )
        .first()
    )
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    cases = (
        db.query(EvaluationCase)
        .filter(EvaluationCase.dataset_version_id == version.id)
        .order_by(EvaluationCase.name)
        .all()
    )
    return VersionDetail(
        id=version.id,
        version_number=version.version_number,
        case_count=len(cases),
        created_at=version.created_at,
        cases=[_case_response(c) for c in cases],
    )


@router.post(
    "/datasets/{dataset_id}/versions/{version_id}/cases",
    response_model=CaseResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_case(
    dataset_id: uuid.UUID,
    version_id: uuid.UUID,
    body: CaseCreate,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> CaseResponse:
    _get_user_dataset(dataset_id, user, db)
    version = (
        db.query(EvaluationDatasetVersion)
        .filter(
            EvaluationDatasetVersion.id == version_id,
            EvaluationDatasetVersion.dataset_id == dataset_id,
        )
        .first()
    )
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    case = EvaluationCase(dataset_version_id=version.id)
    _apply_case_fields(case, body)
    db.add(case)
    db.commit()
    db.refresh(case)
    return _case_response(case)


@router.patch("/cases/{case_id}", response_model=CaseResponse)
def update_case(
    case_id: uuid.UUID, body: CaseUpdate, user: CurrentUser, db: Session = Depends(get_db)
) -> CaseResponse:
    case = (
        db.query(EvaluationCase)
        .join(
            EvaluationDatasetVersion,
            EvaluationDatasetVersion.id == EvaluationCase.dataset_version_id,
        )
        .join(EvaluationDataset, EvaluationDataset.id == EvaluationDatasetVersion.dataset_id)
        .filter(EvaluationCase.id == case_id, EvaluationDataset.user_id == user.id)
        .first()
    )
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    _apply_case_fields(case, body)
    db.commit()
    db.refresh(case)
    return _case_response(case)


@router.delete("/cases/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_case(case_id: uuid.UUID, user: CurrentUser, db: Session = Depends(get_db)) -> None:
    case = (
        db.query(EvaluationCase)
        .join(
            EvaluationDatasetVersion,
            EvaluationDatasetVersion.id == EvaluationCase.dataset_version_id,
        )
        .join(EvaluationDataset, EvaluationDataset.id == EvaluationDatasetVersion.dataset_id)
        .filter(EvaluationCase.id == case_id, EvaluationDataset.user_id == user.id)
        .first()
    )
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    db.delete(case)
    db.commit()


@router.post("/datasets/{dataset_id}/import")
async def import_cases(
    dataset_id: uuid.UUID,
    user: CurrentUser,
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
) -> dict:
    dataset = _get_user_dataset(dataset_id, user, db)
    version = _latest_version(db, dataset.id)
    if not version:
        raise HTTPException(status_code=400, detail="Dataset has no version")
    payload = await file.read()
    name = (file.filename or "").lower()
    try:
        if name.endswith(".csv"):
            parsed = parse_cases_csv(payload)
        else:
            parsed = parse_cases_json(payload)
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    for row in parsed:
        case = EvaluationCase(dataset_version_id=version.id)
        _apply_case_fields(case, row)
        db.add(case)
    db.commit()
    return {"imported": len(parsed), "version_id": str(version.id)}


@router.get("/datasets/{dataset_id}/export")
def export_cases(
    dataset_id: uuid.UUID,
    user: CurrentUser,
    db: Session = Depends(get_db),
    format: str = Query("json", pattern="^(json|csv)$"),
    version_id: uuid.UUID | None = None,
) -> Response:
    dataset = _get_user_dataset(dataset_id, user, db)
    if version_id:
        version = (
            db.query(EvaluationDatasetVersion)
            .filter(
                EvaluationDatasetVersion.id == version_id,
                EvaluationDatasetVersion.dataset_id == dataset.id,
            )
            .first()
        )
    else:
        version = _latest_version(db, dataset.id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    cases = (
        db.query(EvaluationCase)
        .filter(EvaluationCase.dataset_version_id == version.id)
        .order_by(EvaluationCase.name)
        .all()
    )
    if format == "csv":
        content = export_cases_csv(cases)
        media = "text/csv"
    else:
        content = export_cases_json(cases)
        media = "application/json"
    return Response(
        content=content,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{dataset.name}.{format}"'},
    )


@router.post("/runs/estimate", response_model=RunEstimateResponse)
def estimate_run(
    body: RunEstimateRequest, user: CurrentUser, db: Session = Depends(get_db)
) -> RunEstimateResponse:
    version = (
        db.query(AgentVersion)
        .join(Agent, Agent.id == AgentVersion.agent_id)
        .filter(AgentVersion.id == body.agent_version_id, Agent.user_id == user.id)
        .first()
    )
    if not version:
        raise HTTPException(status_code=404, detail="Agent version not found")
    dv = (
        db.query(EvaluationDatasetVersion)
        .join(EvaluationDataset, EvaluationDataset.id == EvaluationDatasetVersion.dataset_id)
        .filter(
            EvaluationDatasetVersion.id == body.dataset_version_id,
            EvaluationDataset.user_id == user.id,
        )
        .first()
    )
    if not dv:
        raise HTTPException(status_code=404, detail="Dataset version not found")
    if not get_preset(body.preset_id):
        raise HTTPException(status_code=400, detail="Unknown preset")

    cost, count, warnings = estimate_evaluation(
        db,
        agent_version_id=body.agent_version_id,
        dataset_version_id=body.dataset_version_id,
        mode=body.mode.value,
        preset_id=body.preset_id,
        include_semantic=body.include_semantic,
        judge_enabled=resolve_judge_enabled(body.mode, body.judge_enabled),
    )
    return RunEstimateResponse(
        estimated_cost=cost,
        case_count=count,
        mode=body.mode,
        warnings=warnings,
    )


@router.post("/runs", response_model=RunSummary, status_code=status.HTTP_201_CREATED)
def start_run(body: RunCreate, user: CurrentUser, db: Session = Depends(get_db)) -> RunSummary:
    version = (
        db.query(AgentVersion)
        .join(Agent, Agent.id == AgentVersion.agent_id)
        .filter(AgentVersion.id == body.agent_version_id, Agent.user_id == user.id)
        .first()
    )
    if not version:
        raise HTTPException(status_code=404, detail="Agent version not found")
    dv = (
        db.query(EvaluationDatasetVersion)
        .join(EvaluationDataset, EvaluationDataset.id == EvaluationDatasetVersion.dataset_id)
        .filter(
            EvaluationDatasetVersion.id == body.dataset_version_id,
            EvaluationDataset.user_id == user.id,
        )
        .first()
    )
    if not dv:
        raise HTTPException(status_code=404, detail="Dataset version not found")

    judge_on = resolve_judge_enabled(body.mode, body.judge_enabled)

    run = EvaluationRun(
        agent_version_id=body.agent_version_id,
        dataset_version_id=body.dataset_version_id,
        mode=body.mode,
        judge_enabled=judge_on,
        judge_model=body.judge_model,
        config_snapshot={
            "preset_id": body.preset_id,
            "include_semantic": body.include_semantic,
            "judge_rubric_template_id": str(body.judge_rubric_template_id)
            if body.judge_rubric_template_id
            else None,
            "progress": {"completed_cases": 0, "total_cases": 0},
        },
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    run_evaluation_task.delay(str(run.id))

    return RunSummary(
        id=run.id,
        agent_version_id=run.agent_version_id,
        dataset_version_id=run.dataset_version_id,
        mode=run.mode,
        status=run.status,
        judge_enabled=run.judge_enabled,
        pass_rate=float(run.pass_rate) if run.pass_rate is not None else None,
        total_cost=float(run.total_cost) if run.total_cost is not None else None,
        progress=run.config_snapshot.get("progress", {}),
        started_at=run.started_at,
        completed_at=run.completed_at,
    )


@router.get("/runs", response_model=list[RunSummary])
def list_runs(user: CurrentUser, db: Session = Depends(get_db)) -> list[RunSummary]:
    runs = (
        db.query(EvaluationRun)
        .join(AgentVersion, AgentVersion.id == EvaluationRun.agent_version_id)
        .join(Agent, Agent.id == AgentVersion.agent_id)
        .filter(Agent.user_id == user.id)
        .order_by(EvaluationRun.started_at.desc())
        .limit(50)
        .all()
    )
    return [
        RunSummary(
            id=r.id,
            agent_version_id=r.agent_version_id,
            dataset_version_id=r.dataset_version_id,
            mode=r.mode,
            status=r.status,
            judge_enabled=r.judge_enabled,
            pass_rate=float(r.pass_rate) if r.pass_rate is not None else None,
            total_cost=float(r.total_cost) if r.total_cost is not None else None,
            progress=(r.config_snapshot or {}).get("progress", {}),
            started_at=r.started_at,
            completed_at=r.completed_at,
        )
        for r in runs
    ]


@router.get("/runs/{run_id}", response_model=RunDetail)
def get_run(run_id: uuid.UUID, user: CurrentUser, db: Session = Depends(get_db)) -> RunDetail:
    run = _user_run(db, run_id, user.id)
    results = (
        db.query(EvaluationResult, EvaluationCase)
        .join(EvaluationCase, EvaluationCase.id == EvaluationResult.case_id)
        .filter(EvaluationResult.run_id == run.id)
        .order_by(EvaluationCase.name)
        .all()
    )
    result_rows: list[ResultResponse] = []
    for result, case in results:
        metrics = db.query(MetricResult).filter(MetricResult.result_id == result.id).all()
        human = (
            db.query(HumanReview).filter(HumanReview.evaluation_result_id == result.id).first()
        )
        judge_row = (
            db.query(JudgeResult)
            .filter(JudgeResult.evaluation_result_id == result.id)
            .order_by(JudgeResult.created_at.desc())
            .first()
        )
        result_rows.append(
            ResultResponse(
                id=result.id,
                case_id=result.case_id,
                case_name=case.name,
                status=result.status,
                actual_answer=result.actual_answer,
                overall_pass=result.overall_pass,
                failure_explanation=result.failure_explanation,
                latency_ms=result.latency_ms,
                tokens=result.tokens,
                cost=float(result.cost),
                metrics=[
                    MetricResultResponse(
                        metric_name=m.metric_name,
                        metric_type=m.metric_type.value,
                        passed=m.passed,
                        score=float(m.score) if m.score is not None else None,
                        threshold=float(m.threshold) if m.threshold is not None else None,
                        details=m.details or {},
                    )
                    for m in metrics
                ],
                human_review=_human_review_response(human) if human else None,
                judge_overall_score=float(judge_row.overall_score)
                if judge_row and judge_row.overall_score is not None
                else None,
            )
        )
    return RunDetail(
        id=run.id,
        agent_version_id=run.agent_version_id,
        dataset_version_id=run.dataset_version_id,
        mode=run.mode,
        status=run.status,
        judge_enabled=run.judge_enabled,
        pass_rate=float(run.pass_rate) if run.pass_rate is not None else None,
        total_cost=float(run.total_cost) if run.total_cost is not None else None,
        progress=(run.config_snapshot or {}).get("progress", {}),
        started_at=run.started_at,
        completed_at=run.completed_at,
        config_snapshot=run.config_snapshot or {},
        results=result_rows,
    )


@router.post("/runs/{run_id}/cancel", response_model=RunSummary)
def cancel_run(run_id: uuid.UUID, user: CurrentUser, db: Session = Depends(get_db)) -> RunSummary:
    run = _user_run(db, run_id, user.id)
    if run.status in (RunStatus.completed, RunStatus.failed):
        raise HTTPException(status_code=400, detail="Run already finished")
    run.status = RunStatus.cancelled
    run.completed_at = datetime.now(run.started_at.tzinfo)
    db.commit()
    db.refresh(run)
    return RunSummary(
        id=run.id,
        agent_version_id=run.agent_version_id,
        dataset_version_id=run.dataset_version_id,
        mode=run.mode,
        status=run.status,
        judge_enabled=run.judge_enabled,
        pass_rate=float(run.pass_rate) if run.pass_rate is not None else None,
        total_cost=float(run.total_cost) if run.total_cost is not None else None,
        progress=(run.config_snapshot or {}).get("progress", {}),
        started_at=run.started_at,
        completed_at=run.completed_at,
    )


@router.post("/results/{result_id}/review", response_model=HumanReviewResponse)
def submit_result_review(
    result_id: uuid.UUID,
    body: HumanReviewCreate,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> HumanReviewResponse:
    result = (
        db.query(EvaluationResult)
        .join(EvaluationRun, EvaluationRun.id == EvaluationResult.run_id)
        .join(AgentVersion, AgentVersion.id == EvaluationRun.agent_version_id)
        .join(Agent, Agent.id == AgentVersion.agent_id)
        .filter(EvaluationResult.id == result_id, Agent.user_id == user.id)
        .first()
    )
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")

    verdict = _verdict_from_api(body.verdict)
    existing = (
        db.query(HumanReview).filter(HumanReview.evaluation_result_id == result_id).first()
    )
    if existing:
        existing.verdict = verdict
        existing.rating = body.rating
        existing.notes = body.notes
        existing.issue_category = body.issue_category
        existing.suggested_improvement = body.suggested_improvement
        existing.preferred_answer = body.preferred_answer
        review = existing
    else:
        review = HumanReview(
            evaluation_result_id=result_id,
            reviewer_user_id=user.id,
            verdict=verdict,
            rating=body.rating,
            notes=body.notes,
            issue_category=body.issue_category,
            suggested_improvement=body.suggested_improvement,
            preferred_answer=body.preferred_answer,
        )
        db.add(review)
    db.commit()
    db.refresh(review)
    return _human_review_response(review)
