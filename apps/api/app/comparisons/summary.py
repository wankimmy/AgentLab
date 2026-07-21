"""Comparison AI summary generation."""

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import ComparisonRun, RegressionResult


def estimate_summary_cost(comparison: ComparisonRun) -> float:
    return 0.003 if settings.ai_api_key else 0.0


def build_summary_text(comparison: ComparisonRun, regressions: list[RegressionResult]) -> str:
    improved = sum(1 for r in regressions if r.classification.value == "improved")
    regressed = sum(1 for r in regressions if r.classification.value == "regressed")
    unchanged = sum(1 for r in regressions if r.classification.value == "unchanged")
    delta = comparison.pass_rate_delta
    delta_pct = f"{float(delta) * 100:.1f}%" if delta is not None else "n/a"
    lines = [
        "Comparison summary (synthetic analyst):",
        f"- Baseline pass rate: {comparison.baseline_pass_rate}",
        f"- Candidate pass rate: {comparison.candidate_pass_rate}",
        f"- Pass rate delta: {delta_pct}",
        f"- Cases improved: {improved}, regressed: {regressed}, unchanged: {unchanged}",
    ]
    critical = [r for r in regressions if r.classification.value == "regressed" and r.severity == "high"]
    if critical:
        names = ", ".join(r.case_name for r in critical[:5])
        lines.append(f"- Focus regressions: {names}")
    if regressed > improved:
        lines.append("- Recommendation: address regressed cases before release.")
    elif improved >= regressed:
        lines.append("- Recommendation: candidate shows net improvement; validate edge cases.")
    return "\n".join(lines)


def summarize_comparison_sync(db: Session, comparison_id: uuid.UUID) -> str:
    comparison = db.get(ComparisonRun, comparison_id)
    if not comparison:
        raise ValueError("Comparison not found")

    comparison.ai_summary_status = "running"
    db.flush()

    regressions = (
        db.query(RegressionResult)
        .filter(RegressionResult.comparison_run_id == comparison.id)
        .all()
    )
    text = build_summary_text(comparison, regressions)
    comparison.ai_summary = text
    comparison.ai_summary_status = "completed"
    return text
