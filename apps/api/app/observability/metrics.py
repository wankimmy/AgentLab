"""Prometheus metrics."""

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

HTTP_REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)
HTTP_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "path"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
AGENT_TURNS = Counter(
    "agent_turns_total",
    "Agent chat turns completed",
    ["runtime", "provider"],
)
EVAL_RUNS = Counter(
    "evaluation_runs_total",
    "Evaluation runs started",
    ["mode"],
)


def metrics_payload() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST


def record_http_request(method: str, path: str, status: int, duration_sec: float) -> None:
    route = path.split("?")[0]
    if len(route) > 80:
        route = route[:77] + "..."
    HTTP_REQUESTS.labels(method=method, path=route, status=str(status)).inc()
    HTTP_DURATION.labels(method=method, path=route).observe(duration_sec)
