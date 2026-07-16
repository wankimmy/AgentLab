from app.core.config import settings


def test_login_success(client, db):
    from app.core.security import hash_password
    from app.models.entities import User, UserRole

    user = User(
        email="test@example.com",
        password_hash=hash_password("secret123"),
        role=UserRole.owner,
        is_active=True,
    )
    db.add(user)
    db.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "secret123"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"
    assert settings.session_cookie_name in response.cookies


def test_login_failure(client, db):
    from app.core.security import hash_password
    from app.models.entities import User, UserRole

    user = User(
        email="test@example.com",
        password_hash=hash_password("secret123"),
        role=UserRole.owner,
        is_active=True,
    )
    db.add(user)
    db.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "wrong"},
    )
    assert response.status_code == 401


def test_me_requires_auth(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_authenticated(auth_client):
    response = auth_client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert "email" in response.json()


def test_logout(auth_client):
    response = auth_client.post("/api/v1/auth/logout")
    assert response.status_code == 204
    me = auth_client.get("/api/v1/auth/me")
    assert me.status_code == 401
