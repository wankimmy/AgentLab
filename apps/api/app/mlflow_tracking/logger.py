import json
import tempfile
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import Agent, AgentVersion, EvaluationResult, EvaluationRun


def log_evaluation_run(db: Session, run: EvaluationRun) -> str:
    """Return MLflow run id or synthetic id when tracking disabled."""
    version = db.get(AgentVersion, run.agent_version_id)
    agent = db.get(Agent, version.agent_id) if version else None

    results = db.query(EvaluationResult).filter(EvaluationResult.run_id == run.id).all()
    passed = sum(1 for r in results if r.overall_pass)
    total = len(results)
    pass_rate = passed / total if total else 0.0

    params: dict[str, Any] = {
        "agent_id": str(agent.id) if agent else "",
        "agent_version_id": str(run.agent_version_id),
        "dataset_version_id": str(run.dataset_version_id),
        "mode": run.mode.value,
        "judge_enabled": str(run.judge_enabled),
        "judge_model": run.judge_model or "",
    }
    metrics: dict[str, float] = {
        "pass_rate": pass_rate,
        "total_cases": float(total),
        "total_cost": float(run.total_cost or 0),
    }
    if results:
        metrics["avg_latency_ms"] = sum(r.latency_ms for r in results) / len(results)

    uri = (settings.mlflow_tracking_uri or "").strip()
    if not uri:
        synthetic = f"local-{run.id}"
        snapshot = dict(run.config_snapshot or {})
        snapshot["mlflow_synthetic"] = True
        snapshot["mlflow_params"] = params
        snapshot["mlflow_metrics"] = metrics
        run.config_snapshot = snapshot
        return synthetic

    try:
        import mlflow

        mlflow.set_tracking_uri(uri)
        experiment = "agentlab-evaluations"
        mlflow.set_experiment(experiment)
        with mlflow.start_run(run_name=str(run.id)) as active:
            mlflow.log_params({k: str(v) for k, v in params.items()})
            mlflow.log_metrics(metrics)
            with tempfile.TemporaryDirectory() as tmp:
                payload = {
                    "config_snapshot": run.config_snapshot,
                    "results_summary": [
                        {
                            "case_id": str(r.case_id),
                            "overall_pass": r.overall_pass,
                            "status": r.status.value,
                        }
                        for r in results
                    ],
                }
                path = Path(tmp) / "eval_summary.json"
                path.write_text(json.dumps(payload), encoding="utf-8")
                mlflow.log_artifact(str(path))
            return active.info.run_id
    except Exception:
        return f"local-{run.id}"
