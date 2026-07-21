from dataclasses import dataclass
from typing import Any

from app.models.entities import CaseClassification, CaseSeverity, EvaluationCase, EvaluationResult


@dataclass
class CaseComparisonRow:
    case_id: str | None
    case_name: str
    classification: CaseClassification
    severity: str
    baseline_pass: bool
    candidate_pass: bool
    details: dict[str, Any]


def _judge_score(result: EvaluationResult, metrics: list) -> float | None:
    for m in metrics:
        if m.metric_name == "llm_judge" and m.score is not None:
            return float(m.score)
    return None


def compare_eval_runs(
    *,
    baseline_results: list[tuple[EvaluationResult, EvaluationCase, list]],
    candidate_by_case: dict[str, tuple[EvaluationResult, list]],
) -> tuple[list[CaseComparisonRow], float, float]:
    rows: list[CaseComparisonRow] = []
    baseline_passed = 0
    candidate_passed = 0
    total = len(baseline_results)

    for base_result, case, base_metrics in baseline_results:
        key = str(case.id)
        cand = candidate_by_case.get(key)
        if not cand:
            rows.append(
                CaseComparisonRow(
                    case_id=key,
                    case_name=case.name,
                    classification=CaseClassification.unchanged,
                    severity=(
                        case.severity.value
                        if hasattr(case.severity, "value")
                        else str(case.severity)
                    ),
                    baseline_pass=base_result.overall_pass,
                    candidate_pass=False,
                    details={"error": "missing_candidate_result"},
                )
            )
            if base_result.overall_pass:
                baseline_passed += 1
            continue

        cand_result, cand_metrics = cand
        if base_result.overall_pass:
            baseline_passed += 1
        if cand_result.overall_pass:
            candidate_passed += 1

        if base_result.overall_pass and not cand_result.overall_pass:
            classification = CaseClassification.regressed
        elif not base_result.overall_pass and cand_result.overall_pass:
            classification = CaseClassification.improved
        else:
            classification = CaseClassification.unchanged

        base_judge = _judge_score(base_result, base_metrics)
        cand_judge = _judge_score(cand_result, cand_metrics)
        details: dict[str, Any] = {
            "baseline_latency_ms": base_result.latency_ms,
            "candidate_latency_ms": cand_result.latency_ms,
            "baseline_cost": float(base_result.cost),
            "candidate_cost": float(cand_result.cost),
            "category": case.category,
        }
        if base_judge is not None and cand_judge is not None:
            details["judge_delta"] = cand_judge - base_judge

        severity = case.severity.value if hasattr(case.severity, "value") else str(case.severity)
        if classification == CaseClassification.regressed:
            if case.category == "security" or case.severity == CaseSeverity.critical:
                severity = "critical"
            elif case.category in ("tool", "citation", "rag"):
                severity = "high"

        rows.append(
            CaseComparisonRow(
                case_id=key,
                case_name=case.name,
                classification=classification,
                severity=severity,
                baseline_pass=base_result.overall_pass,
                candidate_pass=cand_result.overall_pass,
                details=details,
            )
        )

    base_rate = baseline_passed / total if total else 0.0
    cand_rate = candidate_passed / total if total else 0.0
    return rows, base_rate, cand_rate
