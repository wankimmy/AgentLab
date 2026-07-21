def test_demo_login_and_read_only_mutations(auth_client, db):
    from app.core.config import settings
    from app.seed import seed_demo_user

    settings.demo_email = "demo@agentlab.local"
    settings.demo_password = "demo-readonly"
    seed_demo_user(db)
    db.commit()

    login = auth_client.post(
        "/api/v1/auth/login",
        json={"email": "demo@agentlab.local", "password": "demo-readonly"},
    )
    assert login.status_code == 200
    assert login.json()["role"] == "demo"

    read = auth_client.get("/api/v1/agents")
    assert read.status_code == 200

    blocked = auth_client.post(
        "/api/v1/agents",
        json={"name": "Demo blocked agent", "system_prompt": "test"},
    )
    assert blocked.status_code == 403
