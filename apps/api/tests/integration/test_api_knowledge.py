def test_knowledge_collection_upload_and_chunks(auth_client, tmp_path, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "uploads_dir", str(tmp_path))
    monkeypatch.setattr(settings, "app_env", "test")

    coll = auth_client.post(
        "/api/v1/knowledge/collections",
        json={"name": "Test KB", "description": "demo"},
    )
    assert coll.status_code == 201
    coll_id = coll.json()["id"]

    md = b"# Procurement\n\nThree-way matching requires PO, receipt, and invoice."
    files = {"file": ("procurement.md", md, "text/markdown")}
    upload = auth_client.post(
        f"/api/v1/knowledge/collections/{coll_id}/documents",
        files=files,
    )
    assert upload.status_code == 201
    doc_id = upload.json()["id"]
    assert upload.json()["status"] == "ready"

    chunks = auth_client.get(f"/api/v1/knowledge/documents/{doc_id}/chunks")
    assert chunks.status_code == 200
    assert len(chunks.json()) >= 1

    text_resp = auth_client.get(f"/api/v1/knowledge/documents/{doc_id}/text")
    assert "Three-way matching" in text_resp.json()["text"]


def test_rag_playground_trace_has_retrieved_chunks(auth_client, tmp_path, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "uploads_dir", str(tmp_path))
    monkeypatch.setattr(settings, "app_env", "test")

    coll = auth_client.post("/api/v1/knowledge/collections", json={"name": "RAG KB"})
    coll_id = coll.json()["id"]
    md = b"# Returns\n\nReturn requests within 30 days with receipt."
    auth_client.post(
        f"/api/v1/knowledge/collections/{coll_id}/documents",
        files={"file": ("returns.md", md, "text/markdown")},
    )

    agent = auth_client.post("/api/v1/agents", json={"name": "RAG Agent"})
    agent_id = agent.json()["id"]
    version_id = agent.json()["active_version"]["id"]

    auth_client.put(
        f"/api/v1/agents/{agent_id}/versions/{version_id}/collections",
        json={"collection_ids": [coll_id]},
    )
    auth_client.patch(
        f"/api/v1/agents/{agent_id}/versions/{version_id}/rag",
        json={
            "rag_enabled": True,
            "retrieval_config": {"top_k": 3, "mode": "hybrid", "threshold": 0},
        },
    )

    conv = auth_client.post(
        "/api/v1/conversations",
        json={"agent_id": agent_id, "agent_version_id": version_id},
    )
    conv_id = conv.json()["id"]
    response = auth_client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "What is the return policy?"},
    )
    assert response.status_code == 200

    detail = auth_client.get(f"/api/v1/conversations/{conv_id}")
    assistant = next(m for m in detail.json()["messages"] if m["role"] == "assistant")
    trace = auth_client.get(f"/api/v1/traces/{assistant['trace_id']}")
    assert trace.status_code == 200
    assert len(trace.json()["retrieved_chunks"]) >= 1


def test_retrieval_debug_endpoint(auth_client, tmp_path, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "uploads_dir", str(tmp_path))
    monkeypatch.setattr(settings, "app_env", "test")

    coll = auth_client.post("/api/v1/knowledge/collections", json={"name": "Debug KB"})
    coll_id = coll.json()["id"]
    auth_client.post(
        f"/api/v1/knowledge/collections/{coll_id}/documents",
        files={"file": ("doc.md", b"# Topic\n\nKeyword searchable content here.", "text/markdown")},
    )

    debug = auth_client.post(
        "/api/v1/knowledge/retrieval/debug",
        json={
            "query": "keyword searchable",
            "collection_ids": [coll_id],
            "retrieval_config": {"mode": "hybrid", "top_k": 5, "threshold": 0},
        },
    )
    assert debug.status_code == 200
    assert len(debug.json()["chunks"]) >= 1
