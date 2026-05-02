"""Auth flow integration tests: register, login, /me."""


class TestRegister:
    def test_registers_and_creates_tenant(self, client):
        r = client.post(
            "/auth/register",
            json={"email": "a@example.com", "password": "password1234"},
        )
        assert r.status_code == 201
        body = r.json()
        assert body["email"] == "a@example.com"
        assert body["role"] == "owner"
        assert "tenant_id" in body and body["tenant_id"] > 0

    def test_register_with_full_name_and_tenant(self, client):
        r = client.post(
            "/auth/register",
            json={
                "email": "ceo@acme.com",
                "password": "password1234",
                "full_name": "Ada Lovelace",
                "tenant_name": "Acme Corp",
            },
        )
        assert r.status_code == 201
        assert r.json()["full_name"] == "Ada Lovelace"

    def test_duplicate_email_rejected(self, client):
        client.post("/auth/register", json={"email": "b@x.com", "password": "password1234"})
        r = client.post("/auth/register", json={"email": "b@x.com", "password": "password1234"})
        assert r.status_code == 400
        assert "already" in r.json()["detail"].lower()

    def test_short_password_rejected(self, client):
        r = client.post("/auth/register", json={"email": "c@x.com", "password": "short"})
        assert r.status_code == 422

    def test_invalid_email_rejected(self, client):
        r = client.post("/auth/register", json={"email": "not-an-email", "password": "password1234"})
        assert r.status_code == 422

    def test_missing_fields_rejected(self, client):
        r = client.post("/auth/register", json={"email": "d@x.com"})
        assert r.status_code == 422


class TestLogin:
    def test_login_returns_bearer_token(self, client):
        client.post("/auth/register", json={"email": "a@x.com", "password": "password1234"})
        r = client.post("/auth/login", data={"username": "a@x.com", "password": "password1234"})
        assert r.status_code == 200
        body = r.json()
        assert body["token_type"] == "bearer"
        assert body["access_token"]

    def test_login_wrong_password(self, client):
        client.post("/auth/register", json={"email": "a@x.com", "password": "password1234"})
        r = client.post("/auth/login", data={"username": "a@x.com", "password": "WRONG"})
        assert r.status_code == 401

    def test_login_unknown_user(self, client):
        r = client.post("/auth/login", data={"username": "ghost@x.com", "password": "password1234"})
        assert r.status_code == 401


class TestProtectedEndpoint:
    def test_me_without_token(self, client):
        r = client.get("/auth/me")
        assert r.status_code == 401

    def test_me_with_invalid_token(self, client):
        r = client.get("/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
        assert r.status_code == 401

    def test_me_with_garbage_subject(self, client):
        # Token whose 'sub' doesn't map to any user
        from app.core.security import create_access_token

        token = create_access_token(subject=999_999)
        r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401

    def test_me_returns_current_user(self, auth_client):
        r = auth_client.get("/auth/me")
        assert r.status_code == 200
        assert r.json()["email"] == "owner@example.com"


class TestHealth:
    def test_health_is_open(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}
