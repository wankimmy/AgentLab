def test_stream_message_returns_sse(auth_client):
    agent = auth_client.post("/api/v1/agents", json={"name": "Stream Agent"})
    agent_id = agent.json()["id"]
    version_id = agent.json()["active_version"]["id"]
    conv = auth_client.post(
        "/api/v1/conversations",
        json={"agent_id": agent_id, "agent_version_id": version_id},
    )
    conv_id = conv.json()["id"]

    response = auth_client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "How do I create a PO?"},
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
    body = response.text
    assert "event: done" in body
    assert "trace_id" in body

    detail = auth_client.get(f"/api/v1/conversations/{conv_id}")
    assistant = next(m for m in detail.json()["messages"] if m["role"] == "assistant")
    assert "[mock:" in assistant["content"]
    assert assistant["trace_id"]

    trace = auth_client.get(f"/api/v1/traces/{assistant['trace_id']}")
    assert trace.status_code == 200
    data = trace.json()
    assert data["duration_ms"] >= 0
    assert data["input_tokens"] >= 0
    assert data["output_tokens"] >= 0
