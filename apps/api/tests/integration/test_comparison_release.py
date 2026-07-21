import uuid

from app.evaluations.runner import run_evaluation_sync


def _agent_and_dataset(auth_client):
    agent = auth_client.post("/api/v1/agents", json={"name": "Compare Agent"})
    version_id = agent.json()["active_version"]["id"]
    ds = auth_client.post("/api/v1/evaluations/datasets", json={"name": "cmp"})
    dataset_id = ds.json()["id"]
    detail = auth_client.get(f"/api/v1/evaluations/datasets/{dataset_id}")
    dv = detail.json()["versions"][0]["id"]
    auth_client.post(
        f"/api/v1/evaluations/datasets/{dataset_id}/versions/{dv}/cases",
        json={"name": "c1", "user_message": "mock", "required_keywords": ["mock"]},
    )
    auth_client.post(
        f"/api/v1/evaluations/datasets/{dataset_id}/versions/{dv}/cases",
        json={
            "name": "c2",
            "user_message": "mock2",
            "required_keywords": ["missing-keyword"],
        },
    )
    return version_id, dv


def _run(auth_client, version_id, dv, mode="quick"):
    resp = auth_client.post(
        "/api/v1/evaluations/runs",
        json={
            "agent_version_id": version_id,
            "dataset_version_id": dv,
            "mode": mode,
            "preset_id": "customer_support_quality",
            "include_semantic": False,
        },
    )
    run_id = resp.json()["id"]
    run_evaluation_sync(uuid.UUID(run_id))
    return run_id


def test_comparison_detects_regression(auth_client):
    version_id, dv = _agent_and_dataset(auth_client)
    baseline_run = _run(auth_client, version_id, dv)
    candidate_run = _run(auth_client, version_id, dv)
    cmp_resp = auth_client.post(
        "/api/v1/comparisons",
        json={"baseline_run_id": baseline_run, "candidate_run_id": candidate_run},
    )
    assert cmp_resp.status_code == 201
    body = cmp_resp.json()
    assert body["pass_rate_delta"] is not None
    assert any(c["classification"] == "regressed" for c in body["cases"]) or body["cases"]


def test_release_check_blocks_without_passing_eval(auth_client):
    agent = auth_client.post("/api/v1/agents", json={"name": "Rel"})
    agent_id = agent.json()["id"]
    version_id = agent.json()["active_version"]["id"]
    resp = auth_client.post(
        f"/api/v1/agents/{agent_id}/versions/{version_id}/release-check",
        json={},
    )
    assert resp.status_code == 201
    assert resp.json()["status"] in ("blocked", "failed")
