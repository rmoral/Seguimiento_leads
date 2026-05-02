"""Phase 3 background-job logic (sync_all_inboxes + reminder tasks).

Run the service functions directly with the in-memory test DB and a
fake email provider — no Celery broker needed.
"""
from datetime import datetime, timedelta, timezone

from freezegun import freeze_time

from app.models import Contact, EmailAccount, FollowUp, Lead, Tenant, User
from app.services.crypto import encrypt_json
from app.services.reminders import (
    create_followups_for_silent_leads,
    send_daily_digest,
    sync_all_inboxes,
)


# ---------- Helpers ----------


def _make_tenant_user(db, email="x@example.com", reminder_after_days=7, enabled=True):
    from app.core.security import hash_password

    tenant = Tenant(
        name="W",
        reminder_after_days=reminder_after_days,
        auto_reminders_enabled=enabled,
    )
    db.add(tenant)
    db.flush()
    user = User(
        tenant_id=tenant.id,
        email=email,
        password_hash=hash_password("password1234"),
    )
    db.add(user)
    db.commit()
    return tenant, user


def _add_account(db, tenant_id, user_id, email="user@gmail.com"):
    acc = EmailAccount(
        tenant_id=tenant_id,
        user_id=user_id,
        provider="gmail",
        email=email,
        oauth_tokens=encrypt_json({"token": "x"}),
    )
    db.add(acc)
    db.commit()
    return acc


def _add_lead(db, tenant_id, **overrides):
    payload = {"tenant_id": tenant_id, "name": "Lead", "email": "lead@x.com", "status": "contacted"}
    payload.update(overrides)
    lead = Lead(**payload)
    db.add(lead)
    db.commit()
    return lead


def _add_contact(db, lead_id, direction="out", days_ago=0):
    when = datetime.now(timezone.utc) - timedelta(days=days_ago)
    c = Contact(
        lead_id=lead_id,
        direction=direction,
        type="email",
        sent_at=when,
        subject="x",
        body="y",
    )
    db.add(c)
    db.commit()
    return c


# ---------- sync_all_inboxes ----------


class TestSyncAllInboxes:
    def test_runs_for_each_account(self, db_session, fake_provider):
        t, u = _make_tenant_user(db_session)
        _add_account(db_session, t.id, u.id, "a@gmail.com")
        _add_account(db_session, t.id, u.id, "b@gmail.com")

        result = sync_all_inboxes(db_session, get_provider_fn=lambda _n: fake_provider)
        assert result.accounts_processed == 2
        assert result.accounts_failed == 0

    def test_one_account_failure_does_not_break_others(self, db_session, fake_provider):
        t, u = _make_tenant_user(db_session)
        _add_account(db_session, t.id, u.id, "a@gmail.com")
        _add_account(db_session, t.id, u.id, "b@gmail.com")

        calls = {"n": 0}

        def flaky(name):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("API down")
            return fake_provider

        result = sync_all_inboxes(db_session, get_provider_fn=flaky)
        assert result.accounts_processed == 1
        assert result.accounts_failed == 1


# ---------- create_followups_for_silent_leads ----------


class TestCreateFollowupsForSilentLeads:
    def test_creates_followup_for_silent_lead(self, db_session):
        t, _ = _make_tenant_user(db_session, reminder_after_days=7)
        lead = _add_lead(db_session, t.id)
        _add_contact(db_session, lead.id, direction="out", days_ago=10)

        created = create_followups_for_silent_leads(db_session)
        assert created == 1
        fus = db_session.query(FollowUp).filter_by(lead_id=lead.id).all()
        assert len(fus) == 1
        assert fus[0].status == "pending"
        assert "7 días" in fus[0].notes

    def test_skips_recently_contacted_lead(self, db_session):
        t, _ = _make_tenant_user(db_session, reminder_after_days=7)
        lead = _add_lead(db_session, t.id)
        _add_contact(db_session, lead.id, direction="out", days_ago=3)

        assert create_followups_for_silent_leads(db_session) == 0

    def test_skips_lead_that_replied(self, db_session):
        t, _ = _make_tenant_user(db_session, reminder_after_days=7)
        lead = _add_lead(db_session, t.id)
        _add_contact(db_session, lead.id, direction="out", days_ago=15)
        _add_contact(db_session, lead.id, direction="in", days_ago=10)

        assert create_followups_for_silent_leads(db_session) == 0

    def test_skips_terminal_status(self, db_session):
        t, _ = _make_tenant_user(db_session, reminder_after_days=7)
        for status in ("won", "lost", "cold"):
            lead = _add_lead(db_session, t.id, status=status, name=f"L-{status}")
            _add_contact(db_session, lead.id, direction="out", days_ago=20)

        assert create_followups_for_silent_leads(db_session) == 0

    def test_skips_when_pending_followup_already_exists(self, db_session):
        t, _ = _make_tenant_user(db_session, reminder_after_days=7)
        lead = _add_lead(db_session, t.id)
        _add_contact(db_session, lead.id, direction="out", days_ago=10)
        db_session.add(
            FollowUp(
                lead_id=lead.id,
                scheduled_at=datetime.now(timezone.utc),
                status="pending",
                notes="manual",
            )
        )
        db_session.commit()

        assert create_followups_for_silent_leads(db_session) == 0
        # Still only the one we added manually
        assert db_session.query(FollowUp).count() == 1

    def test_skips_when_tenant_disabled(self, db_session):
        t, _ = _make_tenant_user(db_session, reminder_after_days=7, enabled=False)
        lead = _add_lead(db_session, t.id)
        _add_contact(db_session, lead.id, direction="out", days_ago=20)

        assert create_followups_for_silent_leads(db_session) == 0

    def test_skips_lead_never_contacted(self, db_session):
        t, _ = _make_tenant_user(db_session, reminder_after_days=7)
        _add_lead(db_session, t.id)  # no contacts
        assert create_followups_for_silent_leads(db_session) == 0

    def test_respects_per_tenant_threshold(self, db_session):
        # Tenant A: 30 days
        ta, _ = _make_tenant_user(db_session, email="a@x.com", reminder_after_days=30)
        lead_a = _add_lead(db_session, ta.id)
        _add_contact(db_session, lead_a.id, direction="out", days_ago=10)

        # Tenant B: 5 days, same age
        tb, _ = _make_tenant_user(db_session, email="b@x.com", reminder_after_days=5)
        lead_b = _add_lead(db_session, tb.id)
        _add_contact(db_session, lead_b.id, direction="out", days_ago=10)

        created = create_followups_for_silent_leads(db_session)
        assert created == 1
        fus = db_session.query(FollowUp).all()
        assert len(fus) == 1
        assert fus[0].lead_id == lead_b.id


# ---------- send_daily_digest ----------


class TestSendDailyDigest:
    def test_sends_to_user_with_pending_followups(self, db_session, fake_provider):
        t, u = _make_tenant_user(db_session)
        _add_account(db_session, t.id, u.id)
        lead = _add_lead(db_session, t.id, name="Acme Corp")
        db_session.add(
            FollowUp(
                lead_id=lead.id,
                scheduled_at=datetime.now(timezone.utc) - timedelta(hours=1),
                status="pending",
                notes="Auto",
            )
        )
        db_session.commit()

        result = send_daily_digest(
            db_session, get_provider_fn=lambda _n: fake_provider
        )
        assert result.users_notified == 1
        assert len(fake_provider.sent) == 1
        sent = fake_provider.sent[0]
        assert sent["to"] == u.email
        assert "Acme Corp" in sent["body"]
        assert "1 seguimiento" in sent["subject"]

    def test_skips_users_without_account(self, db_session, fake_provider):
        t, u = _make_tenant_user(db_session)
        lead = _add_lead(db_session, t.id)
        db_session.add(
            FollowUp(
                lead_id=lead.id,
                scheduled_at=datetime.now(timezone.utc),
                status="pending",
            )
        )
        db_session.commit()

        result = send_daily_digest(
            db_session, get_provider_fn=lambda _n: fake_provider
        )
        assert result.users_notified == 0
        assert result.users_skipped_no_account == 1
        assert fake_provider.sent == []

    def test_skips_users_without_pending_followups(self, db_session, fake_provider):
        t, u = _make_tenant_user(db_session)
        _add_account(db_session, t.id, u.id)

        result = send_daily_digest(
            db_session, get_provider_fn=lambda _n: fake_provider
        )
        assert result.users_notified == 0
        assert result.users_skipped_no_followups == 1

    def test_does_not_resend_same_day(self, db_session, fake_provider):
        t, u = _make_tenant_user(db_session)
        _add_account(db_session, t.id, u.id)
        lead = _add_lead(db_session, t.id)
        db_session.add(
            FollowUp(
                lead_id=lead.id,
                scheduled_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
                status="pending",
            )
        )
        db_session.commit()

        with freeze_time("2026-05-02 09:00:00"):
            first = send_daily_digest(
                db_session, get_provider_fn=lambda _n: fake_provider
            )
        assert first.users_notified == 1

        with freeze_time("2026-05-02 18:00:00"):
            second = send_daily_digest(
                db_session, get_provider_fn=lambda _n: fake_provider
            )

        assert second.users_notified == 0
        assert second.users_skipped_already_sent_today == 1
        assert len(fake_provider.sent) == 1

    def test_resends_next_day(self, db_session, fake_provider):
        t, u = _make_tenant_user(db_session)
        _add_account(db_session, t.id, u.id)
        lead = _add_lead(db_session, t.id)
        db_session.add(
            FollowUp(
                lead_id=lead.id,
                scheduled_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
                status="pending",
            )
        )
        db_session.commit()

        with freeze_time("2026-05-02 09:00:00"):
            send_daily_digest(db_session, get_provider_fn=lambda _n: fake_provider)
        with freeze_time("2026-05-03 09:00:00"):
            second = send_daily_digest(
                db_session, get_provider_fn=lambda _n: fake_provider
            )
        assert second.users_notified == 1
        assert len(fake_provider.sent) == 2

    def test_provider_failure_does_not_advance_marker(self, db_session, fake_provider):
        t, u = _make_tenant_user(db_session)
        _add_account(db_session, t.id, u.id)
        lead = _add_lead(db_session, t.id)
        db_session.add(
            FollowUp(
                lead_id=lead.id,
                scheduled_at=datetime.now(timezone.utc),
                status="pending",
            )
        )
        db_session.commit()

        def boom(_name):
            class P:
                def send_message(self, **_kw):
                    raise RuntimeError("network down")

            return P()

        result = send_daily_digest(db_session, get_provider_fn=boom)
        assert result.users_notified == 0
        # last_digest_sent_at not set → next run will retry
        db_session.expire_all()
        assert db_session.query(User).filter_by(id=u.id).one().last_digest_sent_at is None
