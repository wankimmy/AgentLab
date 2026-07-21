import time
import uuid

from app.evaluations.runner import run_evaluation_sync


def _create_agent(auth_client):
    response = auth_client.post("/api/v1/agents", json={"name": "Judge Agent"})
    assert response.status_code == 201
    data = response.json()
    return data["id"], data["active_version"]["id"]


def _assistant_message(auth_client, version_id: str, agent_id: str) -> str:
    conv = auth_client.post(
        "/api/v1/conversations",
        json={
            "agent_id": agent_id,
            "agent_version_id": version_id,
            "title": "judge test",
        },
    )
    assert conv.status_code == 201
    conv_id = conv.json()["id"]
    send = auth_client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "Hello mock"},
    )
    assert send.status_code == 200
    detail = auth_client.get(f"/api/v1/conversations/{conv_id}")
    messages = detail.json()["messages"]
    assistant = next(m for m in messages if m["role"] == "assistant")
    return assistant["id"]


def test_message_judge(auth_client):
    agent_id, version_id = _create_agent(auth_client)
    message_id = _assistant_message(auth_client, version_id, agent_id)
    resp = auth_client.post(
        f"/api/v1/messages/{message_id}/judge",
        json={},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["overall_score"] > 0
    assert "criteria_scores" in body
    assert body["limitations_notice"]


def test_multi_judge_review(auth_client):
    agent_id, version_id = _create_agent(auth_client)
    message_id = _assistant_message(auth_client, version_id, agent_id)
    resp = auth_client.post(
        "/api/v1/judges/multi-review",
        json={"message_id": message_id},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["judges"]) == 3
    assert data["mean_overall_score"] > 0


def test_standard_eval_with_judge(auth_client):
    _, version_id = _create_agent(auth_client)
    ds = auth_client.post("/api/v1/evaluations/datasets", json={"name": "Judge DS"})
    dataset_id = ds.json()["id"]
    detail = auth_client.get(f"/api/v1/evaluations/datasets/{dataset_id}")
    version_id_ds = detail.json()["versions"][0]["id"]
    auth_client.post(
        f"/api/v1/evaluations/datasets/{dataset_id}/versions/{version_id_ds}/cases",
        json={
            "name": "pass-case",
            "user_message": "mock test",
            "required_keywords": ["mock"],
        },
    )

    run_resp = auth_client.post(
        "/api/v1/evaluations/runs",
        json={
            "agent_version_id": version_id,
            "dataset_version_id": version_id_ds,
            "mode": "standard",
            "preset_id": "customer_support_quality",
            "include_semantic": False,
            "judge_enabled": True,
        },
    )
    assert run_resp.status_code == 201
    assert run_resp.json().get("judge_enabled") is True
    run_id = run_resp.json()["id"]

    for _ in range(30):
        detail_run = auth_client.get(f"/api/v1/evaluations/runs/{run_id}")
        if detail_run.json()["status"] in ("completed", "failed"):
            break
        time.sleep(0.1)
    else:
        run_evaluation_sync(uuid.UUID(run_id))

    detail_run = auth_client.get(f"/api/v1/evaluations/runs/{run_id}")
    results = detail_run.json()["results"]
    assert results
    judge_metrics = [m for m in results[0]["metrics"] if m["metric_type"] == "judge"]
    assert judge_metrics
    assert results[0]["judge_overall_score"] is not None


def test_deterministic_failure_not_hidden_by_judge(auth_client):
    _, version_id = _create_agent(auth_client)
    ds = auth_client.post("/api/v1/evaluations/datasets", json={"name": "Det fail"})
    dataset_id = ds.json()["id"]
    detail = auth_client.get(f"/api/v1/evaluations/datasets/{dataset_id}")
    version_id_ds = detail.json()["versions"][0]["id"]
    auth_client.post(
        f"/api/v1/evaluations/datasets/{dataset_id}/versions/{version_id_ds}/cases",
        json={
            "name": "fail-keywords",
            "user_message": "mock test",
            "required_keywords": ["definitely-missing-keyword"],
        },
    )

    run_resp = auth_client.post(
        "/api/v1/evaluations/runs",
        json={
            "agent_version_id": version_id,
            "dataset_version_id": version_id_ds,
            "mode": "standard",
            "preset_id": "customer_support_quality",
            "include_semantic": False,
            "judge_enabled": True,
        },
    )
    run_id = run_resp.json()["id"]
    run_evaluation_sync(uuid.UUID(run_id))
    detail_run = auth_client.get(f"/api/v1/evaluations/runs/{run_id}")
    result = detail_run.json()["results"][0]
    assert result["overall_pass"] is False
    judge_metrics = [m for m in result["metrics"] if m["metric_name"] == "llm_judge"]
    if judge_metrics and judge_metrics[0]["passed"]:
        assert result["overall_pass"] is False


def test_human_review_on_result(auth_client):
    _, version_id = _create_agent(auth_client)
    ds = auth_client.post("/api/v1/evaluations/datasets", json={"name": "HR"})
    dataset_id = ds.json()["id"]
    detail = auth_client.get(f"/api/v1/evaluations/datasets/{dataset_id}")
    version_id_ds = detail.json()["versions"][0]["id"]
    auth_client.post(
        f"/api/v1/evaluations/datasets/{dataset_id}/versions/{version_id_ds}/cases",
        json={"name": "c1", "user_message": "mock", "required_keywords": ["mock"]},
    )
    run_resp = auth_client.post(
        "/api/v1/evaluations/runs",
        json={
            "agent_version_id": version_id,
            "dataset_version_id": version_id_ds,
            "mode": "quick",
            "preset_id": "customer_support_quality",
            "include_semantic": False,
        },
    )
    run_id = run_resp.json()["id"]
    run_evaluation_sync(uuid.UUID(run_id))
    result_id = auth_client.get(f"/api/v1/evaluations/runs/{run_id}").json()["results"][0]["id"]
    review = auth_client.post(
        f"/api/v1/evaluations/results/{result_id}/review",
        json={"verdict": "needs_review", "rating": 3, "notes": "check citations"},
    )
    assert review.status_code == 200
    assert review.json()["verdict"] == "needs_review"
    detail_run = auth_client.get(f"/api/v1/evaluations/runs/{run_id}")
    assert detail_run.json()["results"][0]["human_review"]["notes"] == "check citations"
