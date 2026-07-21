from app.runtimes.langgraph_adapter import _build_prepare_graph


def test_langgraph_prepare_graph_runs():
    graph = _build_prepare_graph()
    out = graph.invoke({"prepared": False, "runtime_label": "langgraph"})
    assert out.get("prepared") is True
