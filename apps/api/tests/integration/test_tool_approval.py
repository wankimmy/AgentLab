import json

from app.models.entities import AuditLog


def _parse_sse_events(body: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    event_type = ""
    for line in body.splitlines():
        if line.startswith("event:"):
            event_type = line.split(":", 1)[1].strip()
        elif line.startswith("data:") and event_type:
            events.append((event_type, json.loads(line.split(":", 1)[1].strip())))
            event_type = ""
    return events


def test_calculator_auto_in_playground(auth_client):
    agent = auth_client.post("/api/v1/agents", json={"name": "Calc Agent"})
    agent_id = agent.json()["id"]
    version_id = agent.json()["active_version"]["id"]
    auth_client.patch(
        f"/api/v1/agents/{agent_id}/versions/{version_id}/tools",
        json={
            "tool_config": {
                "calculator": "auto",
                "knowledge_search": "disabled",
                "current_datetime": "disabled",
            }
        },
    )
    conv = auth_client.post(
        "/api/v1/conversations",
        json={"agent_id": agent_id, "agent_version_id": version_id},
    )
    conv_id = conv.json()["id"]

    response = auth_client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "calculate: 2+2"},
    )
    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    event_types = [e[0] for e in events]
    assert "tool_call" in event_types
    assert "tool_result" in event_types
    assert "done" in event_types

    detail = auth_client.get(f"/api/v1/conversations/{conv_id}")
    assistant = next(m for m in detail.json()["messages"] if m["role"] == "assistant")
    trace = auth_client.get(f"/api/v1/traces/{assistant['trace_id']}")
    assert len(trace.json()["tool_results"]) >= 1


def test_tool_approval_flow(auth_client, db):
    agent = auth_client.post("/api/v1/agents", json={"name": "Approval Agent"})
    agent_id = agent.json()["id"]
    version_id = agent.json()["active_version"]["id"]
    auth_client.patch(
        f"/api/v1/agents/{agent_id}/versions/{version_id}/tools",
        json={
            "tool_config": {
                "calculator": "approval",
                "knowledge_search": "disabled",
                "current_datetime": "disabled",
            }
        },
    )
    conv = auth_client.post(
        "/api/v1/conversations",
        json={"agent_id": agent_id, "agent_version_id": version_id},
    )
    conv_id = conv.json()["id"]

    with auth_client.stream(
        "POST",
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "calculate: 3*4"},
    ) as response:
        assert response.status_code == 200
        buffer = ""
        approval_id = None
        for chunk in response.iter_text():
            buffer += chunk
            while "\n\n" in buffer:
                block, buffer = buffer.split("\n\n", 1)
                event_type = ""
                data = None
                for line in block.splitlines():
                    if line.startswith("event:"):
                        event_type = line.split(":", 1)[1].strip()
                    elif line.startswith("data:"):
                        data = json.loads(line.split(":", 1)[1].strip())
                if event_type == "approval_required" and data:
                    approval_id = data["approval_id"]
                    auth_client.post(f"/api/v1/tool-approvals/{approval_id}/approve")
                if event_type == "done":
                    break

    detail = auth_client.get(f"/api/v1/conversations/{conv_id}")
    assistant = next(m for m in detail.json()["messages"] if m["role"] == "assistant")
    trace = auth_client.get(f"/api/v1/traces/{assistant['trace_id']}")
    assert trace.json()["tool_results"]
    audit = db.query(AuditLog).filter(AuditLog.action == "tool.execute").first()
    assert audit is not None
    assert audit.resource_id == "calculator"
