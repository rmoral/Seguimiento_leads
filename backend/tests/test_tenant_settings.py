"""Tenant settings endpoint."""


class TestTenantSettings:
    def test_get_returns_defaults(self, auth_client):
        r = auth_client.get("/tenant/settings")
        assert r.status_code == 200
        body = r.json()
        assert body["reminder_after_days"] == 7
        assert body["auto_reminders_enabled"] is True

    def test_update_partial(self, auth_client):
        r = auth_client.patch(
            "/tenant/settings",
            json={"reminder_after_days": 14, "auto_reminders_enabled": False},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["reminder_after_days"] == 14
        assert body["auto_reminders_enabled"] is False

    def test_update_persists(self, auth_client):
        auth_client.patch("/tenant/settings", json={"reminder_after_days": 5})
        body = auth_client.get("/tenant/settings").json()
        assert body["reminder_after_days"] == 5

    def test_validation_rejects_zero_days(self, auth_client):
        r = auth_client.patch("/tenant/settings", json={"reminder_after_days": 0})
        assert r.status_code == 422

    def test_validation_rejects_huge_days(self, auth_client):
        r = auth_client.patch("/tenant/settings", json={"reminder_after_days": 9999})
        assert r.status_code == 422

    def test_requires_auth(self, client):
        r = client.get("/tenant/settings")
        assert r.status_code == 401

    def test_tenant_isolation(self, two_tenants):
        c = two_tenants["client"]
        c.patch(
            "/tenant/settings",
            json={"reminder_after_days": 30},
            headers=two_tenants["hdr_a"],
        )
        body_b = c.get("/tenant/settings", headers=two_tenants["hdr_b"]).json()
        # B keeps its own defaults
        assert body_b["reminder_after_days"] == 7
