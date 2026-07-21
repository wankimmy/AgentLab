import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.comparisons.regression import evaluate_thresholds
from app.evaluations.judge_policy import resolve_judge_enabled
from app.models.entities import (
    Agent,
    AgentVersion,
    CaseSeverity,
    EvalMode,
    EvaluationCase,
    EvaluationResult,
    EvaluationRun,
    ReleaseCheck,
    ReleaseCheckStatus,
    ReleaseStatus,
    ReleaseThresholdTemplate,
    RunStatus,
)
from app.workers.celery_app import run_evaluation_task


class ReleaseCheckRequest:
    def __init__(
        self,
        *,
        eval_run_id: uuid.UUID | None = None,
        dataset_version_id: uuid.UUID | None = None,
        threshold_template_id: uuid.UUID | None = None,
        preset_id: str = "release_readiness",
    ):
        self.eval_run_id = eval_run_id
        self.dataset_version_id = dataset_version_id
        self.threshold_template_id = threshold_template_id
        self.preset_id = preset_id


def run_release_check(
    db: Session,
    *,
    user_id: uuid.UUID,
    agent_id: uuid.UUID,
    version_id: uuid.UUID,
    eval_run_id: uuid.UUID | None,
    dataset_version_id: uuid.UUID | None,
    threshold_template_id: uuid.UUID | None,
    preset_id: str,
) -> ReleaseCheck:
    version = (
        db.query(AgentVersion)
        .join(Agent, Agent.id == AgentVersion.agent_id)
        .filter(AgentVersion.id == version_id, Agent.id == agent_id, Agent.user_id == user_id)
        .first()
    )
    if not version:
        raise ValueError("Version not found")

    template: ReleaseThresholdTemplate | None = None
    if threshold_template_id:
        template = db.get(ReleaseThresholdTemplate, threshold_template_id)
    if not template:
        template = (
            db.query(ReleaseThresholdTemplate)
            .filter(ReleaseThresholdTemplate.is_system.is_(True))
            .order_by(ReleaseThresholdTemplate.name)
            .first()
        )
    rules = template.rules if template else {"pass_rate": 0.85}

    run: EvaluationRun | None = None
    if eval_run_id:
        run = (
            db.query(EvaluationRun)
            .filter(
                EvaluationRun.id == eval_run_id,
                EvaluationRun.agent_version_id == version_id,
            )
            .first()
        )
    elif dataset_version_id:
        run = EvaluationRun(
            agent_version_id=version_id,
            dataset_version_id=dataset_version_id,
            mode=EvalMode.release,
            judge_enabled=resolve_judge_enabled(EvalMode.release, None),
            config_snapshot={
                "preset_id": preset_id,
                "include_semantic": True,
                "progress": {"completed_cases": 0, "total_cases": 0},
            },
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        run_evaluation_task.delay(str(run.id))
        check = ReleaseCheck(
            agent_version_id=version_id,
            eval_run_id=run.id,
            threshold_template_id=template.id if template else None,
            status=ReleaseCheckStatus.blocked,
            findings={"checks": [{"name": "eval_pending", "passed": False}]},
            created_by=user_id,
            notes="Release evaluation started; re-run check when complete.",
        )
        db.add(check)
        return check

    if not run or run.status != RunStatus.completed:
        check = ReleaseCheck(
            agent_version_id=version_id,
            eval_run_id=run.id if run else None,
            threshold_template_id=template.id if template else None,
            status=ReleaseCheckStatus.blocked,
            findings={"checks": [{"name": "eval_incomplete", "passed": False}]},
            created_by=user_id,
        )
        db.add(check)
        return check

    results = (
        db.query(EvaluationResult, EvaluationCase)
        .join(EvaluationCase, EvaluationCase.id == EvaluationResult.case_id)
        .filter(EvaluationResult.run_id == run.id)
        .all()
    )
    critical_failures = sum(
        1
        for r, c in results
        if not r.overall_pass and c.severity == CaseSeverity.critical
    )
    security_failures = sum(
        1 for r, c in results if not r.overall_pass and c.category == "security"
    )
    pass_rate = float(run.pass_rate or 0)
    regressions: list[dict[str, Any]] = []

    status, findings = evaluate_thresholds(
        pass_rate=pass_rate,
        rules=rules,
        regressions=regressions,
        critical_failures=critical_failures,
        security_failures=security_failures,
    )
    findings["pass_rate"] = pass_rate
    findings["critical_failures"] = critical_failures
    findings["security_failures"] = security_failures

    check = ReleaseCheck(
        agent_version_id=version_id,
        eval_run_id=run.id,
        threshold_template_id=template.id if template else None,
        status=status,
        findings=findings,
        created_by=user_id,
    )
    db.add(check)
    version.release_status = ReleaseStatus.needs_review
    return check


def mark_release_ready(
    db: Session, *, user_id: uuid.UUID, agent_id: uuid.UUID, version_id: uuid.UUID
) -> AgentVersion:
    version = (
        db.query(AgentVersion)
        .join(Agent, Agent.id == AgentVersion.agent_id)
        .filter(AgentVersion.id == version_id, Agent.id == agent_id, Agent.user_id == user_id)
        .first()
    )
    if not version:
        raise ValueError("Version not found")

    latest = (
        db.query(ReleaseCheck)
        .filter(ReleaseCheck.agent_version_id == version_id)
        .order_by(ReleaseCheck.created_at.desc())
        .first()
    )
    if not latest or latest.status != ReleaseCheckStatus.passed:
        raise ValueError("Latest release check must pass before marking release ready")

    version.release_status = ReleaseStatus.release_ready
    return version
