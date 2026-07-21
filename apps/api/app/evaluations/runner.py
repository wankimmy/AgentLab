import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.evaluations.presets import get_preset
from app.judges.rubrics import MAX_JUDGE_CALLS_PER_RUN
from app.judges.service import (
    _criteria_dict,
    load_rubric_template,
    persist_judge_result,
    run_judge_sync,
)
from app.metrics.engine import evaluate_case, resolve_metrics_for_run
from app.metrics.types import CaseInput
from app.mlflow_tracking.logger import log_evaluation_run
from app.models.entities import (
    Agent,
    AgentVersion,
    BackgroundJob,
    CaseStatus,
    ChatTrace,
    EvaluationCase,
    EvaluationResult,
    EvaluationRun,
    JobStatus,
    JudgeSourceType,
    MetricResult,
    MetricType,
    ResultStatus,
    RunStatus,
)
from app.services.cost_service import estimate_cost
from app.services.eval_runtime import run_eval_turn


def estimate_evaluation(
    db: Session,
    *,
    agent_version_id: uuid.UUID,
    dataset_version_id: uuid.UUID,
    mode: str,
    preset_id: str,
    include_semantic: bool,
    judge_enabled: bool = False,
) -> tuple[float, int, list[str]]:
    version = db.get(AgentVersion, agent_version_id)
    if not version:
        raise ValueError("Agent version not found")

    cases = (
        db.query(EvaluationCase)
        .filter(
            EvaluationCase.dataset_version_id == dataset_version_id,
            EvaluationCase.status == CaseStatus.approved,
        )
        .all()
    )
    warnings: list[str] = []
    if not cases:
        warnings.append("No approved cases in dataset version")

    preset = get_preset(preset_id)
    if not preset:
        warnings.append(f"Unknown preset {preset_id}; using defaults")

    per_case = float(estimate_cost(db, version.provider, version.model, 250, 180))
    multiplier = 1.5 if mode == "standard" else 1.0
    if include_semantic and mode == "standard":
        multiplier += 0.2
    if judge_enabled:
        multiplier += 0.5
        warnings.append("LLM judge adds per-case judge API cost")

    total = per_case * len(cases) * multiplier
    if mode == "quick":
        warnings.append("Quick Check uses a reduced metric subset")
    return total, len(cases), warnings


def _update_progress(run: EvaluationRun, completed: int, total: int) -> None:
    snapshot = dict(run.config_snapshot or {})
    snapshot["progress"] = {"completed_cases": completed, "total_cases": total}
    run.config_snapshot = snapshot


def _run_evaluation(db: Session, run_id: uuid.UUID) -> None:
    run = db.get(EvaluationRun, run_id)
    if not run or run.status in (RunStatus.completed, RunStatus.cancelled):
        return

    version = db.get(AgentVersion, run.agent_version_id)
    if not version:
        run.status = RunStatus.failed
        run.completed_at = datetime.now(UTC)
        return

    agent = db.get(Agent, version.agent_id)
    if not agent:
        run.status = RunStatus.failed
        run.completed_at = datetime.now(UTC)
        return

    snapshot = dict(run.config_snapshot or {})
    preset_id = snapshot.get("preset_id", "customer_support_quality")
    preset = get_preset(preset_id) or {}
    metrics = resolve_metrics_for_run(
        preset.get("metrics", ["response_exists"]),
        mode=run.mode.value,
        quick_metrics=preset.get("quick_metrics"),
        include_semantic=snapshot.get("include_semantic", True),
    )
    thresholds = preset.get("thresholds", {})

    cases = (
        db.query(EvaluationCase)
        .filter(
            EvaluationCase.dataset_version_id == run.dataset_version_id,
            EvaluationCase.status == CaseStatus.approved,
        )
        .order_by(EvaluationCase.name)
        .all()
    )

    job = BackgroundJob(
        job_type="run_evaluation",
        status=JobStatus.running,
        payload={"run_id": str(run.id), "total_cases": len(cases)},
    )
    db.add(job)
    run.status = RunStatus.running
    db.flush()

    passed = 0
    total_cost = Decimal("0")
    total = len(cases)
    judge_calls = 0
    rubric_id_raw = snapshot.get("judge_rubric_template_id")
    rubric_template = None
    if rubric_id_raw:
        rubric_template = load_rubric_template(db, uuid.UUID(str(rubric_id_raw)))
    criteria = _criteria_dict(rubric_template)

    try:
        for idx, case in enumerate(cases, start=1):
            db.refresh(run)
            if run.status == RunStatus.cancelled:
                job.status = JobStatus.failed
                job.error = "cancelled"
                break

            case_input = CaseInput.from_entity(case)
            turn = run_eval_turn(
                db,
                version,
                agent.user_id,
                case.user_message,
                conversation_history=case_input.conversation_history,
            )

            trace = db.get(ChatTrace, turn.trace_id) if turn.trace_id else None
            if turn.error:
                result = EvaluationResult(
                    run_id=run.id,
                    case_id=case.id,
                    status=ResultStatus.error,
                    actual_answer=turn.actual_answer,
                    overall_pass=False,
                    failure_explanation=turn.error,
                    trace_id=turn.trace_id,
                )
                db.add(result)
                db.flush()
            else:
                outcomes, overall_pass, explanation = evaluate_case(
                    case_input,
                    turn.actual_answer,
                    trace,
                    metrics=metrics,
                    thresholds=thresholds,
                )
                status = ResultStatus.passed if overall_pass else ResultStatus.failed

                latency = trace.duration_ms if trace else 0
                tokens = (trace.input_tokens + trace.output_tokens) if trace else 0
                cost = trace.estimated_cost if trace else Decimal("0")

                result = EvaluationResult(
                    run_id=run.id,
                    case_id=case.id,
                    status=status,
                    actual_answer=turn.actual_answer,
                    overall_pass=overall_pass,
                    failure_explanation=explanation,
                    trace_id=turn.trace_id,
                    latency_ms=latency,
                    tokens=tokens,
                    cost=cost,
                )
                db.add(result)
                db.flush()

                for outcome in outcomes:
                    db.add(
                        MetricResult(
                            result_id=result.id,
                            metric_name=outcome.metric_name,
                            metric_type=outcome.metric_type,
                            passed=outcome.passed,
                            score=Decimal(str(outcome.score))
                            if outcome.score is not None
                            else None,
                            threshold=(
                                Decimal(str(outcome.threshold))
                                if outcome.threshold is not None
                                else None
                            ),
                            details=outcome.details or {},
                        )
                    )

                det_or_tool_failed = any(
                    not o.passed
                    and o.metric_type in (MetricType.deterministic, MetricType.tool, MetricType.rag)
                    for o in outcomes
                )

                if run.judge_enabled and judge_calls < MAX_JUDGE_CALLS_PER_RUN:
                    judge_calls += 1
                    min_overall = (
                        float(case.min_judge_score) if case.min_judge_score is not None else None
                    )
                    judge_data = run_judge_sync(
                        user_message=case.user_message,
                        assistant_answer=turn.actual_answer,
                        criteria=criteria,
                        expected_answer=case.expected_answer,
                        model=run.judge_model,
                        min_overall=min_overall,
                    )
                    persist_judge_result(
                        db,
                        source_type=JudgeSourceType.evaluation_result,
                        source_id=result.id,
                        rubric_template_id=rubric_template.id if rubric_template else None,
                        data=judge_data,
                        evaluation_result_id=result.id,
                        model=run.judge_model,
                    )
                    cost += Decimal(str(judge_data.estimated_cost))
                    result.cost = cost
                    db.add(
                        MetricResult(
                            result_id=result.id,
                            metric_name="llm_judge",
                            metric_type=MetricType.judge,
                            passed=judge_data.passed,
                            score=Decimal(str(round(judge_data.overall_score, 4))),
                            threshold=(
                                Decimal(str(min_overall)) if min_overall is not None else None
                            ),
                            details={"criteria": judge_data.criteria_scores},
                        )
                    )
                    if not det_or_tool_failed:
                        if not judge_data.passed:
                            overall_pass = False
                            status = ResultStatus.failed
                            explanation = (explanation or "") + "\nJudge: score below threshold."
                            result.overall_pass = False
                            result.status = status
                            result.failure_explanation = explanation

                if case.requires_human_review:
                    result.status = ResultStatus.needs_review

                if overall_pass:
                    passed += 1

                total_cost += cost

            _update_progress(run, idx, total)
            job.payload = {
                **(job.payload or {}),
                "completed_cases": idx,
                "total_cases": total,
            }
            db.flush()

        if run.status != RunStatus.cancelled:
            run.pass_rate = Decimal(str(passed / total)) if total else Decimal("0")
            run.total_cost = total_cost
            run.status = RunStatus.completed
            run.completed_at = datetime.now(UTC)
            job.status = JobStatus.completed
            run.mlflow_run_id = log_evaluation_run(db, run)
    except Exception as exc:
        run.status = RunStatus.failed
        run.completed_at = datetime.now(UTC)
        job.status = JobStatus.failed
        job.error = str(exc)
        snapshot = dict(run.config_snapshot or {})
        snapshot["error"] = str(exc)
        run.config_snapshot = snapshot


def run_evaluation_sync(run_id: uuid.UUID) -> None:
    with SessionLocal() as db:
        _run_evaluation(db, run_id)
        db.commit()
