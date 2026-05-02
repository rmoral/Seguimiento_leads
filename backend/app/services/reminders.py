"""Pure business logic for the Phase 3 background jobs.

The Celery tasks in ``app/tasks`` are thin wrappers around these
functions, which keeps the logic unit-testable without a running broker.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models import Contact, EmailAccount, FollowUp, Lead, Tenant, User
from app.services.email import EmailProvider, get_provider
from app.services.messaging import sync_inbox

logger = logging.getLogger(__name__)

# Final statuses don't need follow-ups.
TERMINAL_STATUSES = {"won", "lost", "cold"}


@dataclass
class SyncOutcome:
    accounts_processed: int
    accounts_failed: int
    total_matched: int


def sync_all_inboxes(db: Session, get_provider_fn=get_provider) -> SyncOutcome:
    """Run an inbox sync against every connected account.

    A failure on one account never prevents the others from syncing.
    """
    accounts = list(db.scalars(select(EmailAccount)).all())
    processed = 0
    failed = 0
    total_matched = 0

    for account in accounts:
        try:
            provider: EmailProvider = get_provider_fn(account.provider)
            result = sync_inbox(db, account, provider)
            processed += 1
            total_matched += result["matched"]
        except Exception as exc:  # broad on purpose, logged
            failed += 1
            logger.warning(
                "Inbox sync failed for account %s (%s): %s",
                account.id,
                account.email,
                exc,
            )
            db.rollback()

    return SyncOutcome(processed, failed, total_matched)


# ---------- Silent-lead detection ----------


def _ensure_utc(value: datetime | None) -> datetime | None:
    """SQLite drops timezone info on read; coerce naive datetimes back to UTC."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _last_contact_at(db: Session, lead_id: int) -> datetime | None:
    last = db.scalar(
        select(Contact)
        .where(Contact.lead_id == lead_id)
        .order_by(Contact.sent_at.desc().nullslast(), Contact.created_at.desc())
        .limit(1)
    )
    if last is None:
        return None
    return _ensure_utc(last.sent_at or last.created_at)


def _has_pending_followup(db: Session, lead_id: int) -> bool:
    return db.scalar(
        select(FollowUp.id)
        .where(FollowUp.lead_id == lead_id, FollowUp.status == "pending")
        .limit(1)
    ) is not None


def create_followups_for_silent_leads(
    db: Session, now: datetime | None = None
) -> int:
    """For each tenant, create a pending FollowUp for leads that:

    - belong to the tenant,
    - have at least one outbound contact,
    - have no inbound response (last contact direction is 'out'),
    - whose last contact happened more than ``reminder_after_days`` ago,
    - are not in a terminal status,
    - and don't already have a pending FollowUp.

    Returns the number of FollowUps created.
    """
    now = now or datetime.now(timezone.utc)
    created = 0

    tenants = list(
        db.scalars(select(Tenant).where(Tenant.auto_reminders_enabled.is_(True))).all()
    )
    for tenant in tenants:
        cutoff = now - timedelta(days=tenant.reminder_after_days)

        leads = list(
            db.scalars(
                select(Lead).where(
                    Lead.tenant_id == tenant.id,
                    ~Lead.status.in_(TERMINAL_STATUSES),
                )
            ).all()
        )
        for lead in leads:
            last = _last_contact_at(db, lead.id)
            if last is None:
                # Never contacted; covered by other workflows, not by silent-lead reminders.
                continue
            if last > cutoff:
                continue
            # Skip if the lead has actually replied (any inbound contact since last outbound).
            last_contact = db.scalar(
                select(Contact)
                .where(Contact.lead_id == lead.id)
                .order_by(Contact.sent_at.desc().nullslast(), Contact.created_at.desc())
                .limit(1)
            )
            if last_contact and last_contact.direction == "in":
                continue
            if _has_pending_followup(db, lead.id):
                continue

            db.add(
                FollowUp(
                    lead_id=lead.id,
                    scheduled_at=now,
                    status="pending",
                    notes=f"Auto: sin respuesta tras {tenant.reminder_after_days} días",
                )
            )
            created += 1

    db.commit()
    return created


# ---------- Daily digest ----------


@dataclass
class DigestOutcome:
    users_notified: int
    users_skipped_no_account: int
    users_skipped_no_followups: int
    users_skipped_already_sent_today: int


def _format_digest(user: User, items: list[tuple[FollowUp, Lead]]) -> tuple[str, str]:
    subject = f"[Seguimiento Leads] {len(items)} seguimiento(s) pendientes"
    lines = [
        f"Hola {user.full_name or user.email},",
        "",
        f"Tienes {len(items)} seguimiento(s) pendientes:",
        "",
    ]
    for fu, lead in items:
        company = f" ({lead.company})" if lead.company else ""
        when = fu.scheduled_at.strftime("%Y-%m-%d")
        notes = f" — {fu.notes}" if fu.notes else ""
        lines.append(f"• {when}: {lead.name}{company}{notes}")
    lines.extend([
        "",
        "Entra en la app para gestionarlos.",
        "",
        "— Seguimiento Leads",
    ])
    return subject, "\n".join(lines)


def send_daily_digest(
    db: Session,
    now: datetime | None = None,
    get_provider_fn=get_provider,
) -> DigestOutcome:
    """Send each user a digest of their pending FollowUps.

    Sent through the user's first connected EmailAccount (so it doesn't
    require any system-level SMTP). Users without an account are skipped
    — they'll see the same data when they log in.
    """
    now = now or datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    notified = 0
    skipped_no_account = 0
    skipped_no_followups = 0
    skipped_already_sent = 0

    users = list(db.scalars(select(User).where(User.is_active.is_(True))).all())
    for user in users:
        last_sent = _ensure_utc(user.last_digest_sent_at)
        if last_sent and last_sent >= today_start:
            skipped_already_sent += 1
            continue

        rows = list(
            db.execute(
                select(FollowUp, Lead)
                .join(Lead, Lead.id == FollowUp.lead_id)
                .where(
                    Lead.tenant_id == user.tenant_id,
                    FollowUp.status == "pending",
                    FollowUp.scheduled_at <= now,
                )
                .order_by(FollowUp.scheduled_at.asc())
            ).all()
        )
        if not rows:
            skipped_no_followups += 1
            continue

        account = db.scalar(
            select(EmailAccount)
            .where(EmailAccount.tenant_id == user.tenant_id)
            .order_by(EmailAccount.created_at.asc())
            .limit(1)
        )
        if account is None:
            skipped_no_account += 1
            continue

        items = [(fu, lead) for fu, lead in rows]
        subject, body = _format_digest(user, items)

        try:
            provider = get_provider_fn(account.provider)
            from app.services.crypto import decrypt_json

            tokens = decrypt_json(account.oauth_tokens) if account.oauth_tokens else {}
            provider.send_message(
                tokens=tokens,
                from_email=account.email,
                to=user.email,
                subject=subject,
                body=body,
            )
        except Exception as exc:
            logger.warning("Digest send failed for user %s: %s", user.id, exc)
            db.rollback()
            continue

        user.last_digest_sent_at = now
        notified += 1

    db.commit()
    return DigestOutcome(
        users_notified=notified,
        users_skipped_no_account=skipped_no_account,
        users_skipped_no_followups=skipped_no_followups,
        users_skipped_already_sent_today=skipped_already_sent,
    )
