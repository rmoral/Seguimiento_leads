"""Contact creation, listing per lead, and tenant isolation."""
from datetime import datetime, timezone


class TestContactCreate:
    def test_create_outbound_email_contact(self, auth_client, make_lead):
        lead = make_lead()
        r = auth_client.post(
            "/contacts",
            json={
                "lead_id": lead["id"],
                "type": "email",
                "direction": "out",
                "subject": "Saludo",
                "body": "Hola",
                "sent_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        assert r.status_code == 201
        body = r.json()
        assert body["lead_id"] == lead["id"]
        assert body["direction"] == "out"

    def test_create_inbound_contact(self, auth_client, make_lead):
        lead = make_lead()
        r = auth_client.post(
            "/contacts",
            json={
                "lead_id": lead["id"],
                "direction": "in",
                "subject": "Re: Saludo",
                "body": "Gracias",
            },
        )
        assert r.status_code == 201
        assert r.json()["direction"] == "in"

    def test_create_with_unknown_lead_returns_404(self, auth_client):
        r = auth_client.post(
            "/contacts", json={"lead_id": 999_999, "subject": "x"}
        )
        assert r.status_code == 404


class TestContactListing:
    def test_list_for_lead(self, auth_client, make_lead):
        lead = make_lead()
        for i in range(3):
            auth_client.post(
                "/contacts",
                json={"lead_id": lead["id"], "subject": f"Msg {i}"},
            )
        r = auth_client.get(f"/contacts/by-lead/{lead['id']}")
        assert r.status_code == 200
        assert len(r.json()) == 3

    def test_list_orders_newest_first(self, auth_client, make_lead):
        lead = make_lead()
        first = auth_client.post(
            "/contacts", json={"lead_id": lead["id"], "subject": "First"}
        ).json()
        second = auth_client.post(
            "/contacts", json={"lead_id": lead["id"], "subject": "Second"}
        ).json()
        body = auth_client.get(f"/contacts/by-lead/{lead['id']}").json()
        assert body[0]["id"] == second["id"]
        assert body[1]["id"] == first["id"]

    def test_list_for_unknown_lead_returns_404(self, auth_client):
        r = auth_client.get("/contacts/by-lead/999999")
        assert r.status_code == 404


class TestContactCascade:
    def test_deleting_lead_cascades_to_contacts(self, auth_client, make_lead):
        lead = make_lead()
        auth_client.post("/contacts", json={"lead_id": lead["id"], "subject": "x"})
        auth_client.delete(f"/leads/{lead['id']}")
        # Lead is gone, so listing returns 404
        r = auth_client.get(f"/contacts/by-lead/{lead['id']}")
        assert r.status_code == 404


class TestContactTenantIsolation:
    def test_b_cannot_create_on_a_lead(self, two_tenants):
        c = two_tenants["client"]
        lead_a = c.post(
            "/leads", json={"name": "A's lead"}, headers=two_tenants["hdr_a"]
        ).json()
        r = c.post(
            "/contacts",
            json={"lead_id": lead_a["id"], "subject": "hacked"},
            headers=two_tenants["hdr_b"],
        )
        assert r.status_code == 404

    def test_b_cannot_list_a_contacts(self, two_tenants):
        c = two_tenants["client"]
        lead_a = c.post(
            "/leads", json={"name": "A's lead"}, headers=two_tenants["hdr_a"]
        ).json()
        c.post(
            "/contacts",
            json={"lead_id": lead_a["id"], "subject": "hi"},
            headers=two_tenants["hdr_a"],
        )
        r = c.get(f"/contacts/by-lead/{lead_a['id']}", headers=two_tenants["hdr_b"])
        assert r.status_code == 404
