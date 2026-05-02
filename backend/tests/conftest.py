import os
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-secret-key-please-change")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture()
def db_session(engine) -> Iterator:
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        for table in reversed(Base.metadata.sorted_tables):
            with engine.begin() as conn:
                conn.exec_driver_sql(f"DELETE FROM {table.name}")


@pytest.fixture()
def client(engine, db_session) -> Iterator[TestClient]:
    def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------- Auth helpers ----------


def _register_and_login(client: TestClient, email: str, password: str = "password1234") -> str:
    """Register a user and return their JWT access token."""
    client.post(
        "/auth/register",
        json={"email": email, "password": password, "tenant_name": f"WS-{email}"},
    )
    res = client.post("/auth/login", data={"username": email, "password": password})
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


@pytest.fixture()
def auth_client(client: TestClient) -> TestClient:
    """Authenticated test client (Tenant A)."""
    token = _register_and_login(client, "owner@example.com")
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture()
def two_tenants(client: TestClient):
    """Two isolated tenants. Returns (token_a, token_b) plus header helpers."""
    token_a = _register_and_login(client, "a@example.com")
    token_b = _register_and_login(client, "b@example.com")

    def hdr(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    return {
        "client": client,
        "token_a": token_a,
        "token_b": token_b,
        "hdr_a": hdr(token_a),
        "hdr_b": hdr(token_b),
    }


# ---------- Resource factories ----------


@pytest.fixture()
def make_lead(auth_client: TestClient):
    def _make(**overrides) -> dict:
        payload = {"name": "Jane Doe", "email": "jane@acme.com", "company": "Acme"}
        payload.update(overrides)
        res = auth_client.post("/leads", json=payload)
        assert res.status_code == 201, res.text
        return res.json()

    return _make


@pytest.fixture()
def make_template(auth_client: TestClient):
    def _make(**overrides) -> dict:
        payload = {
            "name": "First touch",
            "subject": "Hola {name}",
            "body": "Hola {name}, soy …",
            "variables": "name",
        }
        payload.update(overrides)
        res = auth_client.post("/templates", json=payload)
        assert res.status_code == 201, res.text
        return res.json()

    return _make


@pytest.fixture()
def future_iso():
    """A datetime ISO string a few days in the future (UTC)."""

    def _at(days: int = 3) -> str:
        return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()

    return _at
