def test_create_agent_returns_version_one(auth_client):
    response = auth_client.post(
        "/api/v1/agents",
        json={"name": "Test Agent", "system_prompt": "You are a test agent."},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Agent"
    assert data["active_version"] is not None
    assert data["active_version"]["version_number"] == 1
    assert data["active_version"]["system_prompt"] == "You are a test agent."


def test_create_version_does_not_mutate_v1(auth_client):
    create = auth_client.post(
        "/api/v1/agents",
        json={"name": "Version Test", "system_prompt": "Version one prompt."},
    )
    agent_id = create.json()["id"]
    v1_id = create.json()["active_version"]["id"]

    auth_client.post(
        f"/api/v1/agents/{agent_id}/versions",
        json={"system_prompt": "Version two prompt.", "change_summary": "Updated prompt"},
    )

    v1 = auth_client.get(f"/api/v1/agents/{agent_id}/versions/{v1_id}")
    assert v1.json()["system_prompt"] == "Version one prompt."

    versions = auth_client.get(f"/api/v1/agents/{agent_id}/versions")
    assert len(versions.json()) == 2
    assert versions.json()[0]["version_number"] == 2


def test_archive_agent(auth_client):
    create = auth_client.post("/api/v1/agents", json={"name": "Archive Me"})
    agent_id = create.json()["id"]
    response = auth_client.post(f"/api/v1/agents/{agent_id}/archive")
    assert response.status_code == 200
    assert response.json()["status"] == "archived"


def test_list_templates_returns_nine(auth_client):
    response = auth_client.get("/api/v1/templates")
    assert response.status_code == 200
    assert len(response.json()) == 9
