def test_lead_crud_flow(auth_client):
    # Create
    r = auth_client.post(
        "/leads",
        json={"name": "Jane Doe", "email": "jane@acme.com", "company": "Acme"},
    )
    assert r.status_code == 201
    lead = r.json()
    assert lead["status"] == "new"

    # List
    r = auth_client.get("/leads")
    assert r.status_code == 200
    assert len(r.json()) == 1

    # Get
    r = auth_client.get(f"/leads/{lead['id']}")
    assert r.status_code == 200

    # Update
    r = auth_client.patch(f"/leads/{lead['id']}", json={"status": "contacted"})
    assert r.status_code == 200
    assert r.json()["status"] == "contacted"

    # Search
    r = auth_client.get("/leads", params={"q": "jane"})
    assert len(r.json()) == 1

    r = auth_client.get("/leads", params={"status": "new"})
    assert len(r.json()) == 0

    # Delete
    r = auth_client.delete(f"/leads/{lead['id']}")
    assert r.status_code == 204
    r = auth_client.get(f"/leads/{lead['id']}")
    assert r.status_code == 404


def test_leads_isolated_per_tenant(client):
    # Tenant A
    client.post("/auth/register", json={"email": "a@x.com", "password": "password1234"})
    a_token = client.post(
        "/auth/login", data={"username": "a@x.com", "password": "password1234"}
    ).json()["access_token"]
    client.post(
        "/leads",
        json={"name": "Lead A"},
        headers={"Authorization": f"Bearer {a_token}"},
    )

    # Tenant B
    client.post("/auth/register", json={"email": "b@x.com", "password": "password1234"})
    b_token = client.post(
        "/auth/login", data={"username": "b@x.com", "password": "password1234"}
    ).json()["access_token"]

    r = client.get("/leads", headers={"Authorization": f"Bearer {b_token}"})
    assert r.status_code == 200
    assert r.json() == []
