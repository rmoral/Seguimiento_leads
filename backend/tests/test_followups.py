"""FollowUp CRUD, filters, cascading and tenant isolation."""


class TestFollowUpCRUD:
    def test_create_with_lead_only(self, auth_client, make_lead, future_iso):
        lead = make_lead()
        r = auth_client.post(
            "/followups",
            json={"lead_id": lead["id"], "scheduled_at": future_iso(3)},
        )
        assert r.status_code == 201
        body = r.json()
        assert body["status"] == "pending"
        assert body["lead_id"] == lead["id"]

    def test_create_with_template(self, auth_client, make_lead, make_template, future_iso):
        lead = make_lead()
        tpl = make_template()
        r = auth_client.post(
            "/followups",
            json={
                "lead_id": lead["id"],
                "template_id": tpl["id"],
                "scheduled_at": future_iso(7),
                "notes": "send the first-touch template",
            },
        )
        assert r.status_code == 201
        assert r.json()["template_id"] == tpl["id"]

    def test_update_status(self, auth_client, make_lead, future_iso):
        lead = make_lead()
        fu = auth_client.post(
            "/followups",
            json={"lead_id": lead["id"], "scheduled_at": future_iso()},
        ).json()
        r = auth_client.patch(f"/followups/{fu['id']}", json={"status": "done"})
        assert r.status_code == 200
        assert r.json()["status"] == "done"

    def test_delete(self, auth_client, make_lead, future_iso):
        lead = make_lead()
        fu = auth_client.post(
            "/followups",
            json={"lead_id": lead["id"], "scheduled_at": future_iso()},
        ).json()
        r = auth_client.delete(f"/followups/{fu['id']}")
        assert r.status_code == 204


class TestFollowUpListing:
    def test_list_orders_by_scheduled_at_asc(self, auth_client, make_lead, future_iso):
        lead = make_lead()
        far = auth_client.post(
            "/followups", json={"lead_id": lead["id"], "scheduled_at": future_iso(30)}
        ).json()
        soon = auth_client.post(
            "/followups", json={"lead_id": lead["id"], "scheduled_at": future_iso(2)}
        ).json()
        body = auth_client.get("/followups").json()
        assert body[0]["id"] == soon["id"]
        assert body[1]["id"] == far["id"]

    def test_filter_by_status(self, auth_client, make_lead, future_iso):
        lead = make_lead()
        fu1 = auth_client.post(
            "/followups", json={"lead_id": lead["id"], "scheduled_at": future_iso(1)}
        ).json()
        auth_client.post(
            "/followups", json={"lead_id": lead["id"], "scheduled_at": future_iso(2)}
        )
        auth_client.patch(f"/followups/{fu1['id']}", json={"status": "done"})

        body = auth_client.get("/followups", params={"status": "done"}).json()
        assert len(body) == 1
        assert body[0]["status"] == "done"


class TestFollowUpValidation:
    def test_create_unknown_lead_returns_404(self, auth_client, future_iso):
        r = auth_client.post(
            "/followups", json={"lead_id": 999_999, "scheduled_at": future_iso()}
        )
        assert r.status_code == 404

    def test_update_unknown_followup_returns_404(self, auth_client):
        r = auth_client.patch("/followups/999", json={"status": "done"})
        assert r.status_code == 404


class TestFollowUpCascade:
    def test_deleting_lead_cascades_to_followups(self, auth_client, make_lead, future_iso):
        lead = make_lead()
        auth_client.post(
            "/followups", json={"lead_id": lead["id"], "scheduled_at": future_iso()}
        )
        auth_client.delete(f"/leads/{lead['id']}")
        body = auth_client.get("/followups").json()
        assert body == []


class TestFollowUpTenantIsolation:
    def test_b_cannot_see_a_followups(self, two_tenants, future_iso):
        c = two_tenants["client"]
        lead_a = c.post(
            "/leads", json={"name": "A's lead"}, headers=two_tenants["hdr_a"]
        ).json()
        c.post(
            "/followups",
            json={"lead_id": lead_a["id"], "scheduled_at": future_iso()},
            headers=two_tenants["hdr_a"],
        )
        r = c.get("/followups", headers=two_tenants["hdr_b"])
        assert r.json() == []

    def test_b_cannot_create_followup_on_a_lead(self, two_tenants, future_iso):
        c = two_tenants["client"]
        lead_a = c.post(
            "/leads", json={"name": "A's lead"}, headers=two_tenants["hdr_a"]
        ).json()
        r = c.post(
            "/followups",
            json={"lead_id": lead_a["id"], "scheduled_at": future_iso()},
            headers=two_tenants["hdr_b"],
        )
        assert r.status_code == 404
