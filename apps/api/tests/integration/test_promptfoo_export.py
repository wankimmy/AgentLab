def test_promptfoo_export_shape(auth_client, db):
    from app.models.entities import (
        Agent,
        AgentVersion,
        EvaluationCase,
        EvaluationDataset,
        EvaluationDatasetVersion,
        User,
    )
    from app.core.config import settings

    user = db.query(User).filter(User.email == settings.owner_email).first()
    agent = db.query(Agent).filter(Agent.user_id == user.id).first()
    version = db.get(AgentVersion, agent.active_version_id)
    dataset = EvaluationDataset(user_id=user.id, agent_id=agent.id, name="Export test")
    db.add(dataset)
    db.flush()
    dv = EvaluationDatasetVersion(dataset_id=dataset.id, version_number=1)
    db.add(dv)
    db.flush()
    db.add(
        EvaluationCase(
            dataset_version_id=dv.id,
            name="Smoke",
            user_message="Hello",
            category="smoke",
        )
    )
    db.commit()

    response = auth_client.post(
        "/api/v1/exports/promptfoo",
        json={
            "dataset_id": str(dataset.id),
            "agent_version_id": str(version.id),
            "format": "json",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "prompts" in data
    assert "providers" in data
    assert data["tests"][0]["vars"]["query"] == "Hello"
