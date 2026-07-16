import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.evaluations.presets import get_preset
from app.metrics.engine import evaluate_case, resolve_metrics_for_run
from app.metrics.types import CaseInput
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
    MetricResult,
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
                if overall_pass:
                    passed += 1

                latency = trace.duration_ms if trace else 0
                tokens = (trace.input_tokens + trace.output_tokens) if trace else 0
                cost = trace.estimated_cost if trace else Decimal("0")
                total_cost += cost

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
