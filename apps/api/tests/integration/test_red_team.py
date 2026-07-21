def test_red_team_run_and_promote(auth_client):
    agents = auth_client.get("/api/v1/agents")
    assert agents.status_code == 200
    agent = agents.json()["items"][0]
    versions = auth_client.get(f"/api/v1/agents/{agent['id']}/versions")
    version_id = versions.json()[0]["id"]

    est = auth_client.post(
        "/api/v1/red-team/runs/estimate",
        json={"agent_version_id": version_id, "confirm": False},
    )
    assert est.status_code == 200
    assert est.json()["case_count"] >= 1

    run = auth_client.post(
        "/api/v1/red-team/runs",
        json={"agent_version_id": version_id, "confirm": True},
    )
    assert run.status_code == 201

    run_id = run.json()["id"]
    detail = auth_client.get(f"/api/v1/red-team/runs/{run_id}")
    assert detail.status_code == 200
    assert detail.json()["status"] in {"completed", "running", "pending"}
    cases = detail.json()["cases"]
    if cases:
        promote = auth_client.post(f"/api/v1/red-team/cases/{cases[0]['id']}/promote")
        assert promote.status_code == 200
        assert "evaluation_case_id" in promote.json()

    audit = auth_client.get("/api/v1/agents")
    assert audit.status_code == 200
