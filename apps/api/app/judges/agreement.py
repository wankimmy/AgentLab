from decimal import Decimal

from app.judges.schemas import JudgeOutputSchema


def compute_passed(
    criteria: dict[str, dict],
    scores: dict[str, float],
    *,
    min_overall: float | None = None,
) -> tuple[float, bool]:
    if not scores:
        return 0.0, False

    overall = sum(scores.values()) / len(scores)
    passed = True
    for name, score in scores.items():
        cfg = criteria.get(name, {})
        threshold = float(cfg.get("threshold", 3))
        if score < threshold:
            passed = False
    if min_overall is not None and overall < min_overall:
        passed = False
    return overall, passed


def validate_and_normalize(
    raw: dict,
    criteria: dict[str, dict],
    *,
    min_overall: float | None = None,
) -> JudgeOutputSchema:
    parsed = JudgeOutputSchema.model_validate(raw)
    score_map = {k: v.score for k, v in parsed.criteria.items()}
    overall, passed = compute_passed(criteria, score_map, min_overall=min_overall)
    return JudgeOutputSchema(
        criteria=parsed.criteria,
        overall_score=overall,
        passed=passed,
        explanation=parsed.explanation,
        evidence=parsed.evidence,
    )


def multi_judge_agreement(overall_scores: list[float]) -> tuple[float, bool]:
    if len(overall_scores) < 2:
        return 100.0, False
    spread = max(overall_scores) - min(overall_scores)
    agreement = max(0.0, 100.0 - spread * 25.0)
    disagreement = spread >= 1.0
    return agreement, disagreement


def mean_score(scores: list[float]) -> float:
    if not scores:
        return 0.0
    return sum(scores) / len(scores)


def estimate_judge_cost_per_case() -> Decimal:
    return Decimal("0.002")
