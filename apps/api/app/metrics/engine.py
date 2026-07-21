from decimal import Decimal

from app.metrics.deterministic import run_deterministic_metrics
from app.metrics.rag import run_rag_metrics
from app.metrics.ragas_adapter import run_ragas_metrics
from app.metrics.semantic import semantic_similarity_metric
from app.metrics.tool_metrics import run_tool_metrics
from app.metrics.types import CaseInput, MetricOutcome, TraceSnapshot
from app.models.entities import ChatTrace, MetricType

ALL_DETERMINISTIC = {
    "response_exists",
    "response_length",
    "required_keyword",
    "forbidden_keyword",
    "forbidden_claim",
    "exact_match",
    "regex_match",
    "structured_schema",
    "citation_present",
    "correct_source_cited",
    "latency_threshold",
    "token_threshold",
    "cost_threshold",
    "refusal_expected",
    "refusal_not_expected",
}

ALL_TOOL = {"expected_tool", "expected_tool_args", "tool_execution_success"}

ALL_RAG = {
    "expected_source_retrieved",
    "relevant_context_retrieved",
    "citation_coverage",
    "citation_correctness",
    "context_relevance",
    "answer_support",
    "correct_no_context_refusal",
    "context_precision",
    "context_recall",
}

ALL_SEMANTIC = {"semantic_similarity"}


def trace_from_entity(trace: ChatTrace | None) -> TraceSnapshot:
    if not trace:
        return TraceSnapshot()
    return TraceSnapshot(
        duration_ms=trace.duration_ms,
        input_tokens=trace.input_tokens,
        output_tokens=trace.output_tokens,
        estimated_cost=trace.estimated_cost or Decimal("0"),
        retrieved_chunks=list(trace.retrieved_chunks or []),
        tool_requests=list(trace.tool_requests or []),
        tool_results=list(trace.tool_results or []),
        errors=trace.errors,
    )


def resolve_metrics_for_run(
    preset_metrics: list[str],
    *,
    mode: str,
    quick_metrics: list[str] | None = None,
    include_semantic: bool = True,
) -> list[str]:
    if mode == "quick" and quick_metrics:
        selected = list(quick_metrics)
    elif mode == "quick":
        selected = [m for m in preset_metrics if m in ALL_DETERMINISTIC or m in ALL_TOOL]
    else:
        selected = list(preset_metrics)

    if not include_semantic:
        selected = [m for m in selected if m not in ALL_SEMANTIC]
    return selected


def evaluate_case(
    case: CaseInput,
    actual_answer: str,
    trace: ChatTrace | None,
    *,
    metrics: list[str],
    thresholds: dict[str, float] | None = None,
) -> tuple[list[MetricOutcome], bool, str | None]:
    thresholds = thresholds or {}
    snap = trace_from_entity(trace)
    outcomes: list[MetricOutcome] = []

    det = run_deterministic_metrics(case, actual_answer, snap)
    tool = run_tool_metrics(case, snap)
    rag = run_rag_metrics(case, actual_answer, snap)
    ragas = run_ragas_metrics(case, actual_answer, snap, metrics)
    sem = semantic_similarity_metric(
        case.expected_answer,
        actual_answer,
        threshold=thresholds.get("semantic_similarity", 0.8),
    )

    pool: dict[str, MetricOutcome] = {}
    for item in det + tool + rag + ragas:
        pool[item.metric_name] = item
    if sem:
        pool[sem.metric_name] = sem

    for name in metrics:
        if name in pool:
            outcomes.append(pool[name])

    failed = [o for o in outcomes if not o.passed]
    critical_failed = [
        o
        for o in failed
        if o.metric_type in (MetricType.deterministic, MetricType.tool, MetricType.rag)
        or (case.severity == "critical" and not o.passed)
    ]

    det_failed = [o for o in failed if o.metric_type == MetricType.deterministic]
    tool_rag_failed = [o for o in failed if o.metric_type in (MetricType.tool, MetricType.rag)]

    overall_pass = len(failed) == 0
    if det_failed or tool_rag_failed:
        overall_pass = False
    elif failed and all(o.metric_type == MetricType.semantic for o in failed):
        overall_pass = False

    if case.severity == "critical" and critical_failed:
        overall_pass = False

    explanation: str | None = None
    if not overall_pass:
        parts = []
        if case.expected_answer:
            parts.append(f"Expected: {case.expected_answer[:500]}")
        parts.append(f"Actual: {actual_answer[:500]}")
        if failed:
            parts.append("Failed metrics: " + ", ".join(o.metric_name for o in failed))
        explanation = "\n".join(parts)

    return outcomes, overall_pass, explanation
