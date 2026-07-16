import json
import re
from decimal import Decimal

from app.metrics.types import CaseInput, MetricOutcome, TraceSnapshot
from app.models.entities import MetricType

REFUSAL_PATTERNS = (
    "cannot",
    "can't",
    "unable",
    "not able",
    "do not have",
    "don't have",
    "not in",
    "not available",
    "cannot provide",
    "sorry",
    "refuse",
    "not supported",
    "outside my",
    "i'm not allowed",
)


def _outcome(
    name: str,
    passed: bool,
    *,
    score: float | None = None,
    threshold: float | None = None,
    details: dict | None = None,
) -> MetricOutcome:
    return MetricOutcome(
        metric_name=name,
        metric_type=MetricType.deterministic,
        passed=passed,
        score=score,
        threshold=threshold,
        details=details or {},
    )


def _looks_like_refusal(text: str) -> bool:
    lower = text.lower()
    return any(p in lower for p in REFUSAL_PATTERNS)


def _refusal_expected(case: CaseInput) -> bool:
    if case.category in {"unsupported", "security", "refusal"}:
        return True
    if case.expected_behaviour and "refuse" in case.expected_behaviour.lower():
        return True
    return False


def run_deterministic_metrics(
    case: CaseInput,
    actual_answer: str,
    trace: TraceSnapshot,
    *,
    min_length: int = 1,
    max_length: int = 10000,
) -> list[MetricOutcome]:
    results: list[MetricOutcome] = []
    answer = actual_answer or ""
    lower = answer.lower()

    results.append(
        _outcome("response_exists", bool(answer.strip()), details={"length": len(answer)})
    )

    length_ok = min_length <= len(answer) <= max_length
    results.append(
        _outcome(
            "response_length",
            length_ok,
            details={"length": len(answer), "min": min_length, "max": max_length},
        )
    )

    if case.required_keywords:
        missing = [kw for kw in case.required_keywords if kw.lower() not in lower]
        results.append(
            _outcome(
                "required_keyword",
                not missing,
                details={"missing": missing, "required": case.required_keywords},
            )
        )

    if case.forbidden_keywords:
        found = [kw for kw in case.forbidden_keywords if kw.lower() in lower]
        results.append(
            _outcome(
                "forbidden_keyword",
                not found,
                details={"found": found, "forbidden": case.forbidden_keywords},
            )
        )

    if case.forbidden_claims:
        found = [claim for claim in case.forbidden_claims if claim.lower() in lower]
        results.append(
            _outcome(
                "forbidden_claim",
                not found,
                details={"found": found, "forbidden": case.forbidden_claims},
            )
        )

    if case.expected_answer is not None:
        results.append(
            _outcome(
                "exact_match",
                answer.strip() == case.expected_answer.strip(),
                details={"expected": case.expected_answer, "actual": answer},
            )
        )

    if case.expected_behaviour and case.expected_behaviour.startswith("regex:"):
        pattern = case.expected_behaviour.split(":", 1)[1].strip()
        matched = bool(re.search(pattern, answer, re.IGNORECASE | re.DOTALL))
        results.append(_outcome("regex_match", matched, details={"pattern": pattern}))

    if case.expected_behaviour and case.expected_behaviour.startswith("json_schema:"):
        schema_raw = case.expected_behaviour.split(":", 1)[1].strip()
        passed = False
        detail: dict = {"schema": schema_raw}
        try:
            parsed = json.loads(answer)
            detail["parsed"] = True
            # Lightweight validation: ensure object with expected keys from schema snippet
            if isinstance(parsed, dict):
                required_keys = re.findall(r'"(\w+)"\s*:', schema_raw)
                missing_keys = [k for k in required_keys if k not in parsed]
                passed = not missing_keys
                detail["missing_keys"] = missing_keys
            else:
                detail["error"] = "not an object"
        except json.JSONDecodeError as exc:
            detail["error"] = str(exc)
        results.append(_outcome("structured_schema", passed, details=detail))

    if case.expected_citation or case.category == "citation":
        cited = bool(re.search(r"\[[^\]]+\]|\([^)]+\)|source:|section:", answer, re.I))
        results.append(_outcome("citation_present", cited, details={"answer": answer[:200]}))

    if case.expected_citation:
        cited_correct = case.expected_citation.lower() in lower
        results.append(
            _outcome(
                "correct_source_cited",
                cited_correct,
                details={"expected": case.expected_citation},
            )
        )

    if case.max_latency_ms is not None:
        results.append(
            _outcome(
                "latency_threshold",
                trace.duration_ms <= case.max_latency_ms,
                score=float(trace.duration_ms),
                threshold=float(case.max_latency_ms),
                details={"actual_ms": trace.duration_ms},
            )
        )

    if case.max_tokens is not None:
        results.append(
            _outcome(
                "token_threshold",
                trace.total_tokens <= case.max_tokens,
                score=float(trace.total_tokens),
                threshold=float(case.max_tokens),
                details={"actual_tokens": trace.total_tokens},
            )
        )

    if case.max_cost is not None:
        cost = float(trace.estimated_cost)
        results.append(
            _outcome(
                "cost_threshold",
                Decimal(str(cost)) <= case.max_cost,
                score=cost,
                threshold=float(case.max_cost),
                details={"actual_cost": cost},
            )
        )

    if _refusal_expected(case):
        refused = _looks_like_refusal(answer)
        results.append(_outcome("refusal_expected", refused, details={"answer": answer[:200]}))
    elif case.category in {"correct", "tool", "citation"}:
        refused = _looks_like_refusal(answer)
        results.append(_outcome("refusal_not_expected", not refused, details={"refused": refused}))

    return results
