import asyncio

from app.core.config import settings
from app.models.entities import AgentVersion, RuntimeType, User
from app.services.eval_runtime import run_eval_turn


def test_langgraph_runtime_eval_turn(auth_client, db):
    agents = auth_client.get("/api/v1/agents")
    agent = agents.json()["items"][0]
    agent_id = agent["id"]

    created = auth_client.post(
        f"/api/v1/agents/{agent_id}/versions",
        json={"runtime_type": "langgraph", "change_summary": "LangGraph test"},
    )
    assert created.status_code == 201
    version_id = created.json()["id"]
    assert created.json()["runtime_type"] == "langgraph"

    version = db.get(AgentVersion, version_id)
    assert version is not None
    assert version.runtime_type == RuntimeType.langgraph

    user = db.query(User).filter(User.email == settings.owner_email).first()
    result = asyncio.run(
        run_eval_turn(db, version, user.id, "Hello from langgraph runtime test")
    )
    assert result.error is None
    assert result.actual_answer


def test_native_runtime_still_default(auth_client):
    agents = auth_client.get("/api/v1/agents")
    agent = agents.json()["items"][0]
    created = auth_client.post(
        f"/api/v1/agents/{agent['id']}/versions",
        json={"runtime_type": "native", "change_summary": "Explicit native"},
    )
    assert created.status_code == 201
    assert created.json()["runtime_type"] == "native"
