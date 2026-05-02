"""OAuth authorize/callback flow + account listing/disconnect."""
from app.models import EmailAccount
from app.services.crypto import decrypt_json
from app.services.oauth_state import make_state


class TestAuthorize:
    def test_authorize_returns_url(self, auth_client, fake_provider, gmail_creds):
        r = auth_client.post("/email-accounts/gmail/authorize")
        assert r.status_code == 200
        url = r.json()["authorization_url"]
        assert url.startswith("https://accounts.fake/auth?state=")

    def test_authorize_unknown_provider_400(self, auth_client, fake_provider):
        r = auth_client.post("/email-accounts/yahoo/authorize")
        assert r.status_code == 400

    def test_authorize_requires_auth(self, client):
        r = client.post("/email-accounts/gmail/authorize")
        assert r.status_code == 401

    def test_authorize_503_when_gmail_not_configured(self, auth_client, monkeypatch):
        monkeypatch.setattr("app.core.config.settings.GMAIL_CLIENT_ID", "")
        monkeypatch.setattr("app.core.config.settings.GMAIL_CLIENT_SECRET", "")
        r = auth_client.post("/email-accounts/gmail/authorize")
        assert r.status_code == 503


class TestCallback:
    def _state_for(self, auth_client) -> tuple[str, dict]:
        me = auth_client.get("/auth/me").json()
        state = make_state(me["id"], me["tenant_id"], "gmail")
        return state, me

    def test_callback_creates_email_account(self, auth_client, fake_provider, db_session):
        state, me = self._state_for(auth_client)
        r = auth_client.get(
            "/email-accounts/gmail/callback",
            params={"code": "good", "state": state},
            follow_redirects=False,
        )
        assert r.status_code == 302  # redirect to frontend
        assert "connected=user%40gmail.com" in r.headers["location"]

        accounts = db_session.query(EmailAccount).all()
        assert len(accounts) == 1
        acc = accounts[0]
        assert acc.tenant_id == me["tenant_id"]
        assert acc.email == "user@gmail.com"
        # Tokens stored encrypted but decrypt back to the original payload
        assert acc.oauth_tokens != "fake-access"
        decoded = decrypt_json(acc.oauth_tokens)
        assert decoded["token"] == "fake-access"

    def test_callback_updates_existing_account(self, auth_client, fake_provider, db_session):
        state, _ = self._state_for(auth_client)
        # First connection
        auth_client.get(
            "/email-accounts/gmail/callback",
            params={"code": "good", "state": state},
            follow_redirects=False,
        )
        # Second connection with new tokens for the same email
        fake_provider._exchange_tokens = {"token": "new-access", "refresh_token": "new-refresh"}
        auth_client.get(
            "/email-accounts/gmail/callback",
            params={"code": "good2", "state": state},
            follow_redirects=False,
        )

        accounts = db_session.query(EmailAccount).all()
        assert len(accounts) == 1
        decoded = decrypt_json(accounts[0].oauth_tokens)
        assert decoded["token"] == "new-access"

    def test_callback_invalid_state_400(self, auth_client, fake_provider):
        r = auth_client.get(
            "/email-accounts/gmail/callback",
            params={"code": "good", "state": "tampered"},
            follow_redirects=False,
        )
        assert r.status_code == 400

    def test_callback_provider_mismatch_400(self, auth_client, fake_provider):
        state, _ = self._state_for(auth_client)
        # Use a different provider in the URL than the state was issued for
        r = auth_client.get(
            "/email-accounts/fake/callback",
            params={"code": "good", "state": state},
            follow_redirects=False,
        )
        assert r.status_code == 400

    def test_callback_provider_failure_502(self, auth_client, fake_provider):
        state, _ = self._state_for(auth_client)
        r = auth_client.get(
            "/email-accounts/gmail/callback",
            params={"code": "BAD", "state": state},
            follow_redirects=False,
        )
        assert r.status_code == 502


class TestListAndDisconnect:
    def _connect(self, client, fake_provider) -> int:
        state, _ = (lambda c=client: (
            make_state(
                c.get("/auth/me").json()["id"],
                c.get("/auth/me").json()["tenant_id"],
                "gmail",
            ),
            None,
        ))()
        client.get(
            "/email-accounts/gmail/callback",
            params={"code": "good", "state": state},
            follow_redirects=False,
        )
        return client.get("/email-accounts").json()[0]["id"]

    def test_list_empty(self, auth_client):
        r = auth_client.get("/email-accounts")
        assert r.status_code == 200
        assert r.json() == []

    def test_list_after_connect(self, auth_client, fake_provider):
        self._connect(auth_client, fake_provider)
        r = auth_client.get("/email-accounts")
        body = r.json()
        assert len(body) == 1
        assert body[0]["provider"] == "gmail"
        assert body[0]["email"] == "user@gmail.com"

    def test_disconnect(self, auth_client, fake_provider):
        acc_id = self._connect(auth_client, fake_provider)
        r = auth_client.delete(f"/email-accounts/{acc_id}")
        assert r.status_code == 204
        assert auth_client.get("/email-accounts").json() == []

    def test_disconnect_unknown_404(self, auth_client):
        r = auth_client.delete("/email-accounts/9999")
        assert r.status_code == 404

    def test_tenant_isolation(self, two_tenants, fake_provider):
        c = two_tenants["client"]
        # Connect as A
        me_a = c.get("/auth/me", headers=two_tenants["hdr_a"]).json()
        state_a = make_state(me_a["id"], me_a["tenant_id"], "gmail")
        c.get(
            "/email-accounts/gmail/callback",
            params={"code": "good", "state": state_a},
            follow_redirects=False,
        )
        # B cannot see it
        r = c.get("/email-accounts", headers=two_tenants["hdr_b"])
        assert r.json() == []
