import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./_test.db")
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
def db_session(engine):
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        # Wipe tables between tests
        for table in reversed(Base.metadata.sorted_tables):
            with engine.begin() as conn:
                conn.exec_driver_sql(f"DELETE FROM {table.name}")


@pytest.fixture()
def client(engine, db_session):
    def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_client(client):
    client.post(
        "/auth/register",
        json={
            "email": "owner@example.com",
            "password": "supersecret123",
            "tenant_name": "Acme",
        },
    )
    res = client.post(
        "/auth/login",
        data={"username": "owner@example.com", "password": "supersecret123"},
    )
    token = res.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client
