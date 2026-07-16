def test_get_progress_defaults(auth_client):
    response = auth_client.get("/api/v1/onboarding/progress")
    assert response.status_code == 200
    data = response.json()
    assert data["current_step"] == 1
    assert data["completed"] is False


def test_save_progress(auth_client):
    response = auth_client.put(
        "/api/v1/onboarding/progress",
        json={"current_step": 3, "step_data": {"define": {"name": "Test Agent"}}},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["current_step"] == 3
    assert data["step_data"]["define"]["name"] == "Test Agent"


def test_define_draft_shape(auth_client):
    response = auth_client.post(
        "/api/v1/onboarding/define-draft",
        json={
            "purpose": "Help finance staff with ERP questions",
            "target_audience": "Finance team",
            "example_questions": ["How do I create a PO?"],
            "risk_level": "medium",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "suggested_name" in data
    assert "suggested_purpose" in data
    assert "draft_notes" in data


def test_complete_onboarding_creates_agent(auth_client):
    auth_client.put(
        "/api/v1/onboarding/progress",
        json={
            "current_step": 8,
            "step_data": {
                "define": {
                    "name": "Onboarding Agent",
                    "purpose": "Test purpose",
                    "target_audience": "Test users",
                },
                "behaviour": {"system_prompt": "You are a test onboarding agent."},
            },
        },
    )
    response = auth_client.post("/api/v1/onboarding/complete")
    assert response.status_code == 200
    assert response.json()["completed"] is True

    agents = auth_client.get("/api/v1/agents")
    assert agents.json()["total"] >= 1
