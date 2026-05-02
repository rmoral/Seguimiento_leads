def test_register_and_login(client):
    r = client.post(
        "/auth/register",
        json={"email": "a@example.com", "password": "password1234"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "a@example.com"
    assert "tenant_id" in body

    r = client.post(
        "/auth/login",
        data={"username": "a@example.com", "password": "password1234"},
    )
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_register_duplicate_email(client):
    client.post("/auth/register", json={"email": "b@example.com", "password": "password1234"})
    r = client.post("/auth/register", json={"email": "b@example.com", "password": "password1234"})
    assert r.status_code == 400


def test_login_wrong_password(client):
    client.post("/auth/register", json={"email": "c@example.com", "password": "password1234"})
    r = client.post("/auth/login", data={"username": "c@example.com", "password": "wrong"})
    assert r.status_code == 401


def test_me_requires_token(client):
    r = client.get("/auth/me")
    assert r.status_code == 401


def test_me_returns_user(auth_client):
    r = auth_client.get("/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == "owner@example.com"
