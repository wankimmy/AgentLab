def test_install_erp_sample_pack_creates_agent(auth_client):
    packs = auth_client.get("/api/v1/sample-packs")
    assert packs.status_code == 200
    erp_pack = next(p for p in packs.json() if p["slug"] == "erp-support")

    response = auth_client.post(f"/api/v1/sample-packs/{erp_pack['id']}/install")
    assert response.status_code == 201
    data = response.json()
    assert "agent_id" in data
    assert data.get("eval_case_count") == 25
    assert data.get("knowledge_doc_count") == 7
    assert data.get("dataset_id")
    assert data.get("collection_id")

    agent = auth_client.get(f"/api/v1/agents/{data['agent_id']}")
    assert agent.status_code == 200
    assert "SYNTHETIC" in (agent.json().get("notes") or "").upper()
