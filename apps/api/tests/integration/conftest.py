import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.db import Base, get_db
from app.core.security import hash_password
from app.main import app
from app.models.entities import User, UserRole
from app.seed import seed_guides, seed_owner, seed_sample_packs, seed_templates, seed_tools

engine = create_engine(settings.database_url)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestingSessionLocal() as db:
        seed_owner(db)
        seed_tools(db)
        seed_templates(db)
        seed_guides(db)
        seed_sample_packs(db)
        db.commit()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_client(client, db):
    user = db.query(User).filter(User.email == settings.owner_email).first()
    if not user:
        user = User(
            email=settings.owner_email,
            password_hash=hash_password(settings.owner_password),
            role=UserRole.owner,
            is_active=True,
        )
        db.add(user)
        db.flush()
    response = client.post(
        "/api/v1/auth/login",
        json={"email": settings.owner_email, "password": settings.owner_password},
    )
    assert response.status_code == 200
    return client
