"""Lead CRUD, filters, search, validation, and tenant isolation."""


class TestLeadCRUD:
    def test_create_lead_with_required_fields_only(self, auth_client):
        r = auth_client.post("/leads", json={"name": "Solo Name"})
        assert r.status_code == 201
        body = r.json()
        assert body["name"] == "Solo Name"
        assert body["status"] == "new"
        assert body["email"] is None

    def test_create_lead_full_payload(self, auth_client):
        r = auth_client.post(
            "/leads",
            json={
                "name": "Jane",
                "email": "jane@acme.com",
                "company": "Acme",
                "phone": "+34 600 000 000",
                "source": "LinkedIn",
                "status": "contacted",
                "notes": "VIP",
            },
        )
        assert r.status_code == 201
        body = r.json()
        assert body["company"] == "Acme"
        assert body["status"] == "contacted"

    def test_get_lead(self, auth_client, make_lead):
        lead = make_lead(name="Foo")
        r = auth_client.get(f"/leads/{lead['id']}")
        assert r.status_code == 200
        assert r.json()["name"] == "Foo"

    def test_update_lead_partial(self, auth_client, make_lead):
        lead = make_lead()
        r = auth_client.patch(f"/leads/{lead['id']}", json={"status": "responded"})
        assert r.status_code == 200
        assert r.json()["status"] == "responded"
        # Other fields preserved
        assert r.json()["name"] == lead["name"]

    def test_delete_lead(self, auth_client, make_lead):
        lead = make_lead()
        r = auth_client.delete(f"/leads/{lead['id']}")
        assert r.status_code == 204
        r = auth_client.get(f"/leads/{lead['id']}")
        assert r.status_code == 404


class TestLeadValidation:
    def test_create_requires_name(self, auth_client):
        r = auth_client.post("/leads", json={"email": "a@b.com"})
        assert r.status_code == 422

    def test_create_invalid_email_rejected(self, auth_client):
        r = auth_client.post("/leads", json={"name": "X", "email": "not-an-email"})
        assert r.status_code == 422

    def test_create_empty_name_rejected(self, auth_client):
        r = auth_client.post("/leads", json={"name": ""})
        assert r.status_code == 422


class TestLeadListing:
    def test_list_empty(self, auth_client):
        r = auth_client.get("/leads")
        assert r.status_code == 200
        assert r.json() == []

    def test_list_returns_all_for_tenant(self, auth_client, make_lead):
        make_lead(name="A")
        make_lead(name="B")
        r = auth_client.get("/leads")
        assert len(r.json()) == 2

    def test_list_orders_by_created_desc(self, auth_client, make_lead):
        first = make_lead(name="First")
        second = make_lead(name="Second")
        body = auth_client.get("/leads").json()
        assert body[0]["id"] == second["id"]
        assert body[1]["id"] == first["id"]

    def test_filter_by_status(self, auth_client, make_lead):
        make_lead(name="A", status="new")
        make_lead(name="B", status="contacted")
        make_lead(name="C", status="contacted")
        r = auth_client.get("/leads", params={"status": "contacted"})
        assert len(r.json()) == 2

    def test_search_by_name(self, auth_client, make_lead):
        make_lead(name="Alice", email="alice@x.com")
        make_lead(name="Bob", email="bob@y.com")
        r = auth_client.get("/leads", params={"q": "alic"})
        assert len(r.json()) == 1
        assert r.json()[0]["name"] == "Alice"

    def test_search_by_company(self, auth_client, make_lead):
        make_lead(name="A", company="Acme")
        make_lead(name="B", company="Globex")
        r = auth_client.get("/leads", params={"q": "globex"})
        assert len(r.json()) == 1

    def test_pagination_limit_and_offset(self, auth_client, make_lead):
        for i in range(5):
            make_lead(name=f"Lead {i}")
        page1 = auth_client.get("/leads", params={"limit": 2, "offset": 0}).json()
        page2 = auth_client.get("/leads", params={"limit": 2, "offset": 2}).json()
        assert len(page1) == 2
        assert len(page2) == 2
        assert {l["id"] for l in page1}.isdisjoint({l["id"] for l in page2})

    def test_limit_capped_at_500(self, auth_client):
        r = auth_client.get("/leads", params={"limit": 1000})
        assert r.status_code == 422


class TestLeadAuth:
    def test_create_requires_auth(self, client):
        r = client.post("/leads", json={"name": "X"})
        assert r.status_code == 401

    def test_list_requires_auth(self, client):
        r = client.get("/leads")
        assert r.status_code == 401


class TestLeadTenantIsolation:
    def test_b_cannot_list_a_leads(self, two_tenants):
        c = two_tenants["client"]
        c.post("/leads", json={"name": "A's lead"}, headers=two_tenants["hdr_a"])
        r = c.get("/leads", headers=two_tenants["hdr_b"])
        assert r.json() == []

    def test_b_cannot_get_a_lead(self, two_tenants):
        c = two_tenants["client"]
        created = c.post(
            "/leads", json={"name": "A's lead"}, headers=two_tenants["hdr_a"]
        ).json()
        r = c.get(f"/leads/{created['id']}", headers=two_tenants["hdr_b"])
        assert r.status_code == 404

    def test_b_cannot_update_a_lead(self, two_tenants):
        c = two_tenants["client"]
        created = c.post(
            "/leads", json={"name": "A's lead"}, headers=two_tenants["hdr_a"]
        ).json()
        r = c.patch(
            f"/leads/{created['id']}",
            json={"status": "lost"},
            headers=two_tenants["hdr_b"],
        )
        assert r.status_code == 404

    def test_b_cannot_delete_a_lead(self, two_tenants):
        c = two_tenants["client"]
        created = c.post(
            "/leads", json={"name": "A's lead"}, headers=two_tenants["hdr_a"]
        ).json()
        r = c.delete(f"/leads/{created['id']}", headers=two_tenants["hdr_b"])
        assert r.status_code == 404
