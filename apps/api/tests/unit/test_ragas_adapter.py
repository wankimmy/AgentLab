from app.metrics.ragas_adapter import run_ragas_metrics
from app.metrics.types import CaseInput, TraceSnapshot


def test_ragas_heuristic_fallback(monkeypatch):
    monkeypatch.setattr("app.metrics.ragas_adapter.ragas_available", lambda: False)
    case = CaseInput(name="Citation", user_message="What is three-way matching?", category="citation")
    trace = TraceSnapshot(retrieved_chunks=[{"content": "three-way matching invoice receipt"}])
    outcomes = run_ragas_metrics(case, "See manual [PO]", trace, ["context_precision", "context_recall"])
    names = {o.metric_name for o in outcomes}
    assert names == {"context_precision", "context_recall"}
    for o in outcomes:
        assert o.details.get("adapter") == "heuristic"
