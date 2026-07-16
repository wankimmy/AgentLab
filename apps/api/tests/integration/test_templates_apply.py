def test_apply_erp_template_creates_agent(auth_client):
    templates = auth_client.get("/api/v1/templates")
    erp = next(t for t in templates.json() if t["slug"] == "erp-support")

    response = auth_client.post(
        f"/api/v1/templates/{erp['id']}/apply",
        json={"name": "My ERP Agent"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "My ERP Agent"
    assert data["active_version"] is not None
    assert len(data["active_version"]["system_prompt"]) > 50
    assert data["active_version"]["tool_config"]


def test_get_erp_template_has_rich_content(auth_client):
    templates = auth_client.get("/api/v1/templates")
    erp = next(t for t in templates.json() if t["slug"] == "erp-support")
    detail = auth_client.get(f"/api/v1/templates/{erp['id']}")
    assert detail.status_code == 200
    data = detail.json()
    assert data["eval_starter_pack"]
    assert data["judge_rubric"]
    assert len(data["example_questions"]) >= 1
