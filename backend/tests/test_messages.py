"""Send + sync flow with the fake provider."""
from datetime import datetime, timezone

from app.services.email.base import EmailMessage
from app.services.oauth_state import make_state


def _connect_account(auth_client, fake_provider) -> int:
    me = auth_client.get("/auth/me").json()
    state = make_state(me["id"], me["tenant_id"], "gmail")
    auth_client.get(
        "/email-accounts/gmail/callback",
        params={"code": "good", "state": state},
        follow_redirects=False,
    )
    return auth_client.get("/email-accounts").json()[0]["id"]


class TestSend:
    def test_send_creates_outbound_contact(self, auth_client, fake_provider, make_lead):
        acc_id = _connect_account(auth_client, fake_provider)
        lead = make_lead(email="jane@acme.com", status="new")

        r = auth_client.post(
            f"/email-accounts/{acc_id}/send",
            json={
                "lead_id": lead["id"],
                "subject": "Hola Jane",
                "body": "Te escribo para…",
            },
        )
        assert r.status_code == 201
        body = r.json()
        assert body["external_id"].startswith("msg-")

        # Provider received the call with the right payload
        assert len(fake_provider.sent) == 1
        sent = fake_provider.sent[0]
        assert sent["to"] == "jane@acme.com"
        assert sent["subject"] == "Hola Jane"

        # Contact stored with direction=out
        contacts = auth_client.get(f"/contacts/by-lead/{lead['id']}").json()
        assert len(contacts) == 1
        assert contacts[0]["direction"] == "out"
        assert contacts[0]["external_id"] == body["external_id"]

        # Lead status auto-promoted from "new" to "contacted"
        updated = auth_client.get(f"/leads/{lead['id']}").json()
        assert updated["status"] == "contacted"

    def test_send_uses_to_override(self, auth_client, fake_provider, make_lead):
        acc_id = _connect_account(auth_client, fake_provider)
        lead = make_lead(email=None)
        r = auth_client.post(
            f"/email-accounts/{acc_id}/send",
            json={
                "lead_id": lead["id"],
                "subject": "Hi",
                "body": "Body",
                "to": "manual@example.com",
            },
        )
        assert r.status_code == 201
        assert fake_provider.sent[0]["to"] == "manual@example.com"

    def test_send_400_when_lead_has_no_email_and_no_override(
        self, auth_client, fake_provider, make_lead
    ):
        acc_id = _connect_account(auth_client, fake_provider)
        lead = make_lead(email=None)
        r = auth_client.post(
            f"/email-accounts/{acc_id}/send",
            json={"lead_id": lead["id"], "subject": "Hi", "body": "Body"},
        )
        assert r.status_code == 400

    def test_send_unknown_lead_404(self, auth_client, fake_provider):
        acc_id = _connect_account(auth_client, fake_provider)
        r = auth_client.post(
            f"/email-accounts/{acc_id}/send",
            json={"lead_id": 99999, "subject": "Hi", "body": "Body"},
        )
        assert r.status_code == 404

    def test_send_unknown_account_404(self, auth_client, fake_provider, make_lead):
        lead = make_lead()
        r = auth_client.post(
            "/email-accounts/9999/send",
            json={"lead_id": lead["id"], "subject": "Hi", "body": "Body"},
        )
        assert r.status_code == 404


class TestSync:
    def _msg(self, **overrides) -> EmailMessage:
        defaults = dict(
            external_id="ext-1",
            thread_id="th-1",
            from_email="jane@acme.com",
            to_email="user@gmail.com",
            subject="Re: Hola",
            body="Cuéntame más",
            received_at=datetime.now(timezone.utc),
        )
        defaults.update(overrides)
        return EmailMessage(**defaults)

    def test_sync_matches_lead_by_email(self, auth_client, fake_provider, make_lead):
        acc_id = _connect_account(auth_client, fake_provider)
        lead = make_lead(email="jane@acme.com", status="contacted")
        fake_provider.queue_message(self._msg())

        r = auth_client.post(f"/email-accounts/{acc_id}/sync")
        assert r.status_code == 200
        body = r.json()
        assert body == {
            "fetched": 1,
            "matched": 1,
            "skipped_duplicates": 0,
            "skipped_unmatched": 0,
        }

        contacts = auth_client.get(f"/contacts/by-lead/{lead['id']}").json()
        assert len(contacts) == 1
        c = contacts[0]
        assert c["direction"] == "in"
        assert c["external_id"] == "ext-1"
        assert c["thread_id"] == "th-1"

        # Lead promoted to "responded"
        assert auth_client.get(f"/leads/{lead['id']}").json()["status"] == "responded"

    def test_sync_email_match_is_case_insensitive(self, auth_client, fake_provider, make_lead):
        acc_id = _connect_account(auth_client, fake_provider)
        lead = make_lead(email="Jane@Acme.com")
        fake_provider.queue_message(self._msg(from_email="jane@acme.com"))

        r = auth_client.post(f"/email-accounts/{acc_id}/sync")
        assert r.json()["matched"] == 1
        assert len(auth_client.get(f"/contacts/by-lead/{lead['id']}").json()) == 1

    def test_sync_skips_unmatched_senders(self, auth_client, fake_provider, make_lead):
        acc_id = _connect_account(auth_client, fake_provider)
        make_lead(email="jane@acme.com")
        fake_provider.queue_message(self._msg(from_email="stranger@nowhere.com"))

        r = auth_client.post(f"/email-accounts/{acc_id}/sync")
        body = r.json()
        assert body["matched"] == 0
        assert body["skipped_unmatched"] == 1

    def test_sync_is_idempotent(self, auth_client, fake_provider, make_lead):
        acc_id = _connect_account(auth_client, fake_provider)
        lead = make_lead(email="jane@acme.com")
        fake_provider.queue_message(self._msg(external_id="dedup-1"))

        first = auth_client.post(f"/email-accounts/{acc_id}/sync").json()
        assert first["matched"] == 1
        assert first["skipped_duplicates"] == 0

        # Second sync with the same message id
        second = auth_client.post(f"/email-accounts/{acc_id}/sync").json()
        assert second["matched"] == 0
        assert second["skipped_duplicates"] == 1

        # Only one inbound contact stored
        contacts = auth_client.get(f"/contacts/by-lead/{lead['id']}").json()
        assert len(contacts) == 1

    def test_sync_unknown_account_404(self, auth_client, fake_provider):
        r = auth_client.post("/email-accounts/9999/sync")
        assert r.status_code == 404

    def test_sync_updates_last_synced_at(self, auth_client, fake_provider, db_session):
        from app.models import EmailAccount

        acc_id = _connect_account(auth_client, fake_provider)
        before = db_session.get(EmailAccount, acc_id).last_synced_at
        assert before is None

        auth_client.post(f"/email-accounts/{acc_id}/sync")
        db_session.expire_all()
        after = db_session.get(EmailAccount, acc_id).last_synced_at
        assert after is not None
