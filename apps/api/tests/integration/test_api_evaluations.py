import time
import uuid

from app.evaluations.runner import run_evaluation_sync


def _create_agent(auth_client):
    response = auth_client.post("/api/v1/agents", json={"name": "Eval Agent"})
    assert response.status_code == 201
    data = response.json()
    return data["id"], data["active_version"]["id"]


def _create_dataset_with_cases(auth_client, count: int = 10):
    ds = auth_client.post(
        "/api/v1/evaluations/datasets",
        json={"name": "Quick Check Pack", "description": "Phase 6 test"},
    )
    assert ds.status_code == 201
    dataset_id = ds.json()["id"]
    detail = auth_client.get(f"/api/v1/evaluations/datasets/{dataset_id}")
    version_id = detail.json()["versions"][0]["id"]

    for i in range(count):
        auth_client.post(
            f"/api/v1/evaluations/datasets/{dataset_id}/versions/{version_id}/cases",
            json={
                "name": f"case-{i}",
                "category": "correct" if i % 2 == 0 else "unsupported",
                "user_message": f"Test question {i}",
                "expected_answer": f"Expected answer {i}" if i % 2 == 0 else None,
                "required_keywords": ["mock"] if i % 2 == 0 else [],
            },
        )
    return version_id


def test_eval_templates(auth_client):
    response = auth_client.get("/api/v1/evaluations/templates")
    assert response.status_code == 200
    presets = response.json()
    assert len(presets) == 8
    assert presets[0]["id"]


def test_dataset_import_export_roundtrip(auth_client):
    ds = auth_client.post(
        "/api/v1/evaluations/datasets",
        json={"name": "Import test"},
    )
    dataset_id = ds.json()["id"]
    detail = auth_client.get(f"/api/v1/evaluations/datasets/{dataset_id}")
    version_id = detail.json()["versions"][0]["id"]
    auth_client.post(
        f"/api/v1/evaluations/datasets/{dataset_id}/versions/{version_id}/cases",
        json={"name": "one", "user_message": "hello", "required_keywords": ["hi"]},
    )
    exported = auth_client.get(f"/api/v1/evaluations/datasets/{dataset_id}/export?format=json")
    assert exported.status_code == 200
    assert b"cases" in exported.content


def test_quick_check_run_with_failure_explanations(auth_client):
    _, version_id = _create_agent(auth_client)
    dataset_version_id = _create_dataset_with_cases(auth_client, 10)

    estimate = auth_client.post(
        "/api/v1/evaluations/runs/estimate",
        json={
            "agent_version_id": version_id,
            "dataset_version_id": dataset_version_id,
            "mode": "quick",
            "preset_id": "customer_support_quality",
            "include_semantic": False,
        },
    )
    assert estimate.status_code == 200
    assert estimate.json()["case_count"] == 10

    run_resp = auth_client.post(
        "/api/v1/evaluations/runs",
        json={
            "agent_version_id": version_id,
            "dataset_version_id": dataset_version_id,
            "mode": "quick",
            "preset_id": "customer_support_quality",
            "include_semantic": False,
        },
    )
    assert run_resp.status_code == 201
    run_id = run_resp.json()["id"]

    # Eager Celery may complete before poll; ensure finished for assertion stability
    for _ in range(30):
        detail = auth_client.get(f"/api/v1/evaluations/runs/{run_id}")
        if detail.json()["status"] in ("completed", "failed"):
            break
        time.sleep(0.1)
    else:
        run_evaluation_sync(uuid.UUID(run_id))

    detail = auth_client.get(f"/api/v1/evaluations/runs/{run_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["status"] == "completed"
    assert len(body["results"]) == 10
    assert body["pass_rate"] is not None

    failed = [r for r in body["results"] if not r["overall_pass"]]
    assert failed
    assert failed[0]["failure_explanation"]
    assert (
        "Failed metrics" in failed[0]["failure_explanation"]
        or "Actual:" in failed[0]["failure_explanation"]
    )

    passed = [r for r in body["results"] if r["overall_pass"]]
    assert passed or body["pass_rate"] < 1.0
