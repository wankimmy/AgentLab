def test_create_conversation(auth_client):
    agent = auth_client.post("/api/v1/agents", json={"name": "Chat Agent"})
    agent_id = agent.json()["id"]
    version_id = agent.json()["active_version"]["id"]

    response = auth_client.post(
        "/api/v1/conversations",
        json={"agent_id": agent_id, "agent_version_id": version_id, "title": "Test chat"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["agent_id"] == agent_id
    assert data["messages"] == []


def test_list_conversations(auth_client):
    create = auth_client.post("/api/v1/agents", json={"name": "List Conv Agent"})
    agent_id = create.json()["id"]
    version_id = create.json()["active_version"]["id"]
    auth_client.post(
        "/api/v1/conversations",
        json={"agent_id": agent_id, "agent_version_id": version_id},
    )
    response = auth_client.get(f"/api/v1/conversations?agent_id={agent_id}")
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_message_feedback(auth_client):
    agent = auth_client.post("/api/v1/agents", json={"name": "Feedback Agent"})
    agent_id = agent.json()["id"]
    version_id = agent.json()["active_version"]["id"]
    conv = auth_client.post(
        "/api/v1/conversations",
        json={"agent_id": agent_id, "agent_version_id": version_id},
    )
    conv_id = conv.json()["id"]

    stream = auth_client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "Hello feedback test"},
    )
    assert stream.status_code == 200
    body = stream.text
    assert "event: token" in body or "event: done" in body

    detail = auth_client.get(f"/api/v1/conversations/{conv_id}")
    assistant = next(m for m in detail.json()["messages"] if m["role"] == "assistant")

    feedback = auth_client.post(
        f"/api/v1/messages/{assistant['id']}/feedback",
        json={"rating": 5, "notes": "Great mock response"},
    )
    assert feedback.status_code == 200
    assert feedback.json()["rating"] == 5
