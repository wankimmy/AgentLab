import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.comparisons.engine import compare_eval_runs
from app.models.entities import (
    Agent,
    AgentVersion,
    CaseClassification,
    ComparisonRun,
    ComparisonRunStatus,
    EvaluationCase,
    EvaluationResult,
    EvaluationRun,
    MetricResult,
    RegressionResult,
    RunStatus,
)


def _load_run_results(
    db: Session, run_id: uuid.UUID
) -> list[tuple[EvaluationResult, EvaluationCase, list]]:
    rows = (
        db.query(EvaluationResult, EvaluationCase)
        .join(EvaluationCase, EvaluationCase.id == EvaluationResult.case_id)
        .filter(EvaluationResult.run_id == run_id)
        .order_by(EvaluationCase.name)
        .all()
    )
    out: list[tuple[EvaluationResult, EvaluationCase, list]] = []
    for result, case in rows:
        metrics = db.query(MetricResult).filter(MetricResult.result_id == result.id).all()
        out.append((result, case, metrics))
    return out


def user_owns_run(db: Session, run_id: uuid.UUID, user_id: uuid.UUID) -> EvaluationRun | None:
    return (
        db.query(EvaluationRun)
        .join(AgentVersion, AgentVersion.id == EvaluationRun.agent_version_id)
        .join(Agent, Agent.id == AgentVersion.agent_id)
        .filter(EvaluationRun.id == run_id, Agent.user_id == user_id)
        .first()
    )


def create_comparison(
    db: Session, user_id: uuid.UUID, baseline_run_id: uuid.UUID, candidate_run_id: uuid.UUID
) -> ComparisonRun:
    baseline = user_owns_run(db, baseline_run_id, user_id)
    candidate = user_owns_run(db, candidate_run_id, user_id)
    if not baseline or not candidate:
        raise ValueError("Run not found")
    if baseline.status != RunStatus.completed or candidate.status != RunStatus.completed:
        raise ValueError("Both runs must be completed")

    comparison = ComparisonRun(
        user_id=user_id,
        baseline_agent_version_id=baseline.agent_version_id,
        candidate_agent_version_id=candidate.agent_version_id,
        baseline_run_id=baseline.id,
        candidate_run_id=candidate.id,
        status=ComparisonRunStatus.running,
    )
    db.add(comparison)
    db.flush()

    base_rows = _load_run_results(db, baseline.id)
    cand_rows = _load_run_results(db, candidate.id)
    cand_map: dict[str, tuple[EvaluationResult, list]] = {}
    for result, case, metrics in cand_rows:
        cand_map[str(case.id)] = (result, metrics)

    case_rows, base_rate, cand_rate = compare_eval_runs(
        baseline_results=base_rows,
        candidate_by_case=cand_map,
    )

    for row in case_rows:
        details = dict(row.details)
        details["baseline_pass"] = row.baseline_pass
        details["candidate_pass"] = row.candidate_pass
        db.add(
            RegressionResult(
                comparison_run_id=comparison.id,
                case_id=uuid.UUID(row.case_id) if row.case_id else None,
                case_name=row.case_name,
                classification=row.classification,
                severity=row.severity,
                details=details,
            )
        )

    comparison.baseline_pass_rate = Decimal(str(round(base_rate, 4)))
    comparison.candidate_pass_rate = Decimal(str(round(cand_rate, 4)))
    comparison.pass_rate_delta = Decimal(str(round(cand_rate - base_rate, 4)))
    comparison.status = ComparisonRunStatus.completed
    comparison.completed_at = datetime.now(UTC)
    comparison.config_snapshot = {
        "improved": sum(1 for r in case_rows if r.classification == CaseClassification.improved),
        "regressed": sum(1 for r in case_rows if r.classification == CaseClassification.regressed),
        "unchanged": sum(1 for r in case_rows if r.classification == CaseClassification.unchanged),
    }
    return comparison
