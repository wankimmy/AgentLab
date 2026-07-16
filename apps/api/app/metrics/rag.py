import re

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
    "not supported",
)


def _chunk_texts(chunks: list) -> list[str]:
    texts: list[str] = []
    for chunk in chunks:
        if isinstance(chunk, dict):
            for key in ("content", "text", "title", "document_title", "source"):
                val = chunk.get(key)
                if isinstance(val, str) and val:
                    texts.append(val.lower())
                    break
        elif isinstance(chunk, str):
            texts.append(chunk.lower())
    return texts


def _chunk_sources(chunks: list) -> list[str]:
    sources: list[str] = []
    for chunk in chunks:
        if not isinstance(chunk, dict):
            continue
        for key in ("document_title", "title", "source", "document_id", "filename"):
            val = chunk.get(key)
            if isinstance(val, str) and val:
                sources.append(val.lower())
    return sources


def run_rag_metrics(
    case: CaseInput,
    actual_answer: str,
    trace: TraceSnapshot,
) -> list[MetricOutcome]:
    results: list[MetricOutcome] = []
    chunks = trace.retrieved_chunks or []
    sources = _chunk_sources(chunks)
    texts = _chunk_texts(chunks)
    lower_answer = actual_answer.lower()

    if case.expected_source:
        expected = case.expected_source.lower()
        found = any(expected in src for src in sources) or any(expected in text for text in texts)
        results.append(
            MetricOutcome(
                metric_name="expected_source_retrieved",
                metric_type=MetricType.rag,
                passed=found,
                details={"expected": case.expected_source, "sources": sources[:5]},
            )
        )

    if case.required_keywords and chunks:
        combined = " ".join(texts)
        overlap = [kw for kw in case.required_keywords if kw.lower() in combined]
        passed = len(overlap) >= max(1, len(case.required_keywords) // 2)
        results.append(
            MetricOutcome(
                metric_name="relevant_context_retrieved",
                metric_type=MetricType.rag,
                passed=passed,
                score=float(len(overlap)),
                details={"overlap": overlap},
            )
        )

    if chunks and actual_answer.strip():
        cited = bool(re.search(r"\[[^\]]+\]|\([^)]+\)|source:|section:", actual_answer, re.I))
        results.append(
            MetricOutcome(
                metric_name="citation_coverage",
                metric_type=MetricType.rag,
                passed=cited,
                details={"retrieved_count": len(chunks)},
            )
        )

    if case.expected_citation and chunks:
        cited_correct = case.expected_citation.lower() in lower_answer
        results.append(
            MetricOutcome(
                metric_name="citation_correctness",
                metric_type=MetricType.rag,
                passed=cited_correct,
                details={"expected": case.expected_citation},
            )
        )

    if case.user_message and chunks:
        query_terms = [t for t in re.findall(r"\w+", case.user_message.lower()) if len(t) > 3]
        combined = " ".join(texts)
        hits = sum(1 for t in query_terms[:8] if t in combined)
        score = hits / max(len(query_terms[:8]), 1)
        results.append(
            MetricOutcome(
                metric_name="context_relevance",
                metric_type=MetricType.rag,
                passed=score >= 0.25,
                score=score,
                threshold=0.25,
            )
        )

    if chunks and case.expected_answer:
        support_terms = [t for t in re.findall(r"\w+", case.expected_answer.lower()) if len(t) > 4][
            :6
        ]
        combined = " ".join(texts)
        supported = sum(1 for t in support_terms if t in combined)
        score = supported / max(len(support_terms), 1)
        results.append(
            MetricOutcome(
                metric_name="answer_support",
                metric_type=MetricType.rag,
                passed=score >= 0.3,
                score=score,
                threshold=0.3,
            )
        )

    if not chunks and case.category in {"unsupported", "refusal"}:
        refused = any(p in lower_answer for p in REFUSAL_PATTERNS)
        results.append(
            MetricOutcome(
                metric_name="correct_no_context_refusal",
                metric_type=MetricType.rag,
                passed=refused,
                details={"no_chunks": True},
            )
        )

    return results
