import math

from app.metrics.types import MetricOutcome
from app.models.entities import MetricType
from app.providers.embeddings import get_embedding_provider

DEFAULT_THRESHOLD = 0.8


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def semantic_similarity_metric(
    expected_answer: str | None,
    actual_answer: str,
    *,
    threshold: float = DEFAULT_THRESHOLD,
) -> MetricOutcome | None:
    if not expected_answer or not expected_answer.strip():
        return None
    if not actual_answer.strip():
        return MetricOutcome(
            metric_name="semantic_similarity",
            metric_type=MetricType.semantic,
            passed=False,
            score=0.0,
            threshold=threshold,
            details={"reason": "empty actual answer"},
        )

    provider = get_embedding_provider()
    vectors = provider.embed([expected_answer.strip(), actual_answer.strip()])
    score = _cosine_similarity(vectors[0], vectors[1])
    return MetricOutcome(
        metric_name="semantic_similarity",
        metric_type=MetricType.semantic,
        passed=score >= threshold,
        score=score,
        threshold=threshold,
        details={
            "notice": "Semantic similarity does not prove factual correctness.",
        },
    )
