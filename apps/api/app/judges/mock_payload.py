import hashlib
from typing import Any

from app.judges.agreement import compute_passed


def mock_judge_payload(
    criteria: dict[str, Any],
    assistant_answer: str,
    judge_index: int | None = None,
) -> dict:
    digest = hashlib.sha256(f"{assistant_answer}:{judge_index}".encode()).hexdigest()
    base = 3.5 + (int(digest[:2], 16) % 15) / 10.0
    if judge_index is not None:
        base = max(1.0, min(5.0, base + (judge_index - 1) * 0.3))
    criteria_out: dict[str, dict] = {}
    for i, name in enumerate(criteria):
        score = max(1.0, min(5.0, base - (i % 3) * 0.2))
        criteria_out[name] = {"score": round(score, 1), "explanation": f"Mock score for {name}"}
    scores = {k: v["score"] for k, v in criteria_out.items()}
    overall, passed = compute_passed(criteria, scores)
    return {
        "criteria": criteria_out,
        "overall_score": round(overall, 2),
        "passed": passed,
        "explanation": "Mock judge evaluation for CI.",
        "evidence": [assistant_answer[:80]] if assistant_answer else [],
    }
