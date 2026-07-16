from app.metrics.deterministic import run_deterministic_metrics
from app.metrics.rag import run_rag_metrics
from app.metrics.semantic import semantic_similarity_metric
from app.metrics.tool_metrics import run_tool_metrics
from app.metrics.types import CaseInput, TraceSnapshot


def _case(**kwargs) -> CaseInput:
    return CaseInput(name="test", **kwargs)


def _trace(**kwargs) -> TraceSnapshot:
    return TraceSnapshot(**kwargs)


def test_required_keyword_pass():
    case = _case(required_keywords=["invoice", "payment"])
    results = run_deterministic_metrics(
        case, "Please check the invoice and payment status.", _trace()
    )
    metric = next(r for r in results if r.metric_name == "required_keyword")
    assert metric.passed


def test_required_keyword_fail():
    case = _case(required_keywords=["citation", "manual"])
    results = run_deterministic_metrics(case, "I do not know.", _trace())
    metric = next(r for r in results if r.metric_name == "required_keyword")
    assert not metric.passed
    assert "citation" in metric.details["missing"]


def test_forbidden_keyword_fail():
    case = _case(forbidden_keywords=["password", "secret"])
    results = run_deterministic_metrics(case, "Here is the password you requested.", _trace())
    metric = next(r for r in results if r.metric_name == "forbidden_keyword")
    assert not metric.passed


def test_refusal_expected_for_unsupported_category():
    case = _case(category="unsupported", user_message="What is my salary?")
    results = run_deterministic_metrics(case, "I cannot provide salary information.", _trace())
    metric = next(r for r in results if r.metric_name == "refusal_expected")
    assert metric.passed


def test_refusal_not_expected_for_correct_category():
    case = _case(category="correct", user_message="How do I create a PO?")
    results = run_deterministic_metrics(
        case, "Open procurement and select create purchase order.", _trace()
    )
    metric = next(r for r in results if r.metric_name == "refusal_not_expected")
    assert metric.passed


def test_latency_threshold():
    case = _case(max_latency_ms=100)
    results = run_deterministic_metrics(case, "ok", _trace(duration_ms=250))
    metric = next(r for r in results if r.metric_name == "latency_threshold")
    assert not metric.passed
    assert metric.score == 250.0


def test_expected_tool_called():
    case = _case(expected_tool="calculator")
    trace = _trace(
        tool_requests=[{"name": "calculator", "arguments": {"expression": "2+2"}}],
        tool_results=[{"name": "calculator", "result": "4"}],
    )
    results = run_tool_metrics(case, trace)
    tool_metric = next(r for r in results if r.metric_name == "expected_tool")
    assert tool_metric.passed


def test_semantic_similarity_identical():
    outcome = semantic_similarity_metric("hello world", "hello world")
    assert outcome is not None
    assert outcome.passed
    assert outcome.score is not None
    assert outcome.score >= 0.99


def test_rag_expected_source_retrieved():
    case = _case(expected_source="ERP Manual")
    trace = _trace(
        retrieved_chunks=[{"document_title": "ERP Manual section 3", "content": "PO steps"}]
    )
    results = run_rag_metrics(case, "See ERP Manual section 3.", trace)
    metric = next(r for r in results if r.metric_name == "expected_source_retrieved")
    assert metric.passed


def test_response_exists():
    case = _case()
    empty = run_deterministic_metrics(case, "", _trace())
    assert not next(r for r in empty if r.metric_name == "response_exists").passed
    filled = run_deterministic_metrics(case, "answer", _trace())
    assert next(r for r in filled if r.metric_name == "response_exists").passed
