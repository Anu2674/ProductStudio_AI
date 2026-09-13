import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app import models  # noqa: F401  ensures all models register with Base.metadata


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = testing_session_local()
    yield session
    session.close()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _isolate_uploads(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))


@pytest.fixture(autouse=True)
def _stub_generation_queue(monkeypatch):
    # generation_service used to enqueue a background job (`generation_queue.enqueue`);
    # it now calls `process_generation` directly and synchronously. Stub that call
    # instead so tests don't hit the real AI service / DB session concurrently.
    from app.services import generation_service

    monkeypatch.setattr(generation_service, "process_generation", lambda *args, **kwargs: None)


@pytest.fixture()
def auth_headers(client):
    def _make(email: str = "owner@example.com", password: str = "StrongPass123"):
        client.post("/api/v1/auth/register", json={"email": email, "password": password})
        response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _make
