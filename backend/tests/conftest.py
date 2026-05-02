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


# ---------- Fake email provider ----------


class FakeEmailProvider:
    """In-memory EmailProvider used by tests in place of Gmail."""

    name = "fake"

    def __init__(self):
        self.sent: list[dict] = []
        self._messages: list = []
        self._exchange_email = "user@gmail.com"
        self._exchange_tokens: dict = {"token": "fake-access", "refresh_token": "fake-refresh"}
        self.next_message_id = 1

    # --- OAuth ---
    def authorization_url(self, state: str) -> str:
        return f"https://accounts.fake/auth?state={state}"

    def exchange_code(self, code: str) -> tuple[str, dict]:
        if code == "BAD":
            raise RuntimeError("invalid grant")
        return self._exchange_email, dict(self._exchange_tokens)

    # --- Messaging ---
    def send_message(self, tokens, from_email, to, subject, body) -> str:
        self.sent.append(
            {"tokens": tokens, "from": from_email, "to": to, "subject": subject, "body": body}
        )
        mid = f"msg-{self.next_message_id}"
        self.next_message_id += 1
        return mid

    def fetch_messages(self, tokens, since=None, max_results=50):
        return list(self._messages)

    # --- Test helpers ---
    def queue_message(self, msg) -> None:
        self._messages.append(msg)

    def reset(self) -> None:
        self.sent.clear()
        self._messages.clear()


@pytest.fixture()
def fake_provider(monkeypatch) -> FakeEmailProvider:
    """A FakeEmailProvider wired into both API routers and the messaging service."""
    from app.api import email_accounts as ea_router
    from app.api import messages as msg_router

    fake = FakeEmailProvider()
    monkeypatch.setattr(ea_router, "get_provider", lambda name: fake)
    monkeypatch.setattr(msg_router, "get_provider", lambda name: fake)
    # Also expose "fake" as a supported provider
    monkeypatch.setattr(
        ea_router, "supported_providers", lambda: ["gmail", "fake"]
    )
    return fake


@pytest.fixture()
def gmail_creds(monkeypatch):
    """Pretend Gmail OAuth is configured for tests that need /authorize to succeed."""
    monkeypatch.setattr("app.core.config.settings.GMAIL_CLIENT_ID", "test-client-id")
    monkeypatch.setattr("app.core.config.settings.GMAIL_CLIENT_SECRET", "test-secret")
