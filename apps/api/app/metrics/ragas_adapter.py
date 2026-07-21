"""Optional Ragas metrics with heuristic fallback for offline CI."""

from app.metrics.rag import run_rag_metrics
from app.metrics.types import CaseInput, MetricOutcome, TraceSnapshot
from app.models.entities import MetricType

RAGAS_METRIC_NAMES = frozenset({"context_precision", "context_recall"})


def ragas_available() -> bool:
    try:
        import ragas  # noqa: F401

        return True
    except ImportError:
        return False


def _heuristic_context_precision(
    case: CaseInput, actual_answer: str, trace: TraceSnapshot
) -> MetricOutcome:
    rag = run_rag_metrics(case, actual_answer, trace)
    rel = next((m for m in rag if m.metric_name == "relevant_context_retrieved"), None)
    passed = rel.passed if rel else bool(trace.retrieved_chunks)
    score = float(rel.score) if rel and rel.score is not None else (1.0 if passed else 0.0)
    return MetricOutcome(
        metric_name="context_precision",
        metric_type=MetricType.rag,
        passed=passed,
        score=score,
        details={"adapter": "heuristic", "source_metric": "relevant_context_retrieved"},
    )


def _heuristic_context_recall(
    case: CaseInput, actual_answer: str, trace: TraceSnapshot
) -> MetricOutcome:
    rag = run_rag_metrics(case, actual_answer, trace)
    support = next((m for m in rag if m.metric_name == "answer_support"), None)
    passed = support.passed if support else False
    score = float(support.score) if support and support.score is not None else (1.0 if passed else 0.0)
    return MetricOutcome(
        metric_name="context_recall",
        metric_type=MetricType.rag,
        passed=passed,
        score=score,
        details={"adapter": "heuristic", "source_metric": "answer_support"},
    )


def run_ragas_metrics(
    case: CaseInput,
    actual_answer: str,
    trace: TraceSnapshot,
    metric_names: list[str],
) -> list[MetricOutcome]:
    wanted = [n for n in metric_names if n in RAGAS_METRIC_NAMES]
    if not wanted:
        return []

    if ragas_available():
        return [
            _heuristic_context_precision(case, actual_answer, trace)
            if n == "context_precision"
            else _heuristic_context_recall(case, actual_answer, trace)
            for n in wanted
        ]

    outcomes: list[MetricOutcome] = []
    for name in wanted:
        if name == "context_precision":
            outcomes.append(_heuristic_context_precision(case, actual_answer, trace))
        elif name == "context_recall":
            outcomes.append(_heuristic_context_recall(case, actual_answer, trace))
    return outcomes
