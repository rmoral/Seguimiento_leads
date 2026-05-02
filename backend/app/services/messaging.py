"""High-level send/sync logic that the API routes consume.

Keeps provider-specific code out of the routers and makes the behaviour
unit-testable with a mocked EmailProvider.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Contact, EmailAccount, Lead
from app.services.crypto import decrypt_json, encrypt_json
from app.services.email import EmailProvider


def _load_tokens(account: EmailAccount) -> dict:
    if not account.oauth_tokens:
        raise ValueError("Account has no stored credentials")
    return decrypt_json(account.oauth_tokens)


def _save_tokens(account: EmailAccount, tokens: dict) -> None:
    account.oauth_tokens = encrypt_json(tokens)


def send_message(
    db: Session,
    account: EmailAccount,
    lead: Lead,
    provider: EmailProvider,
    subject: str,
    body: str,
    to: str | None = None,
) -> Contact:
    target = to or lead.email
    if not target:
        raise ValueError("Lead has no email address and no override was provided")

    tokens = _load_tokens(account)
    external_id = provider.send_message(
        tokens=tokens,
        from_email=account.email,
        to=target,
        subject=subject,
        body=body,
    )

    contact = Contact(
        lead_id=lead.id,
        type="email",
        direction="out",
        subject=subject,
        body=body,
        sent_at=datetime.now(timezone.utc),
        external_id=external_id,
    )
    db.add(contact)
    if lead.status == "new":
        lead.status = "contacted"
    db.commit()
    db.refresh(contact)
    return contact


def sync_inbox(
    db: Session,
    account: EmailAccount,
    provider: EmailProvider,
    max_results: int = 50,
) -> dict[str, int]:
    """Fetch new messages and create inbound Contact rows for matched leads.

    Matching strategy: case-insensitive lookup of the sender's email address
    against `leads.email` within the same tenant. Unmatched messages are
    counted but not stored (Phase 4 will queue them for AI triage).
    """
    tokens = _load_tokens(account)
    messages = provider.fetch_messages(
        tokens=tokens, since=account.last_synced_at, max_results=max_results
    )

    fetched = len(messages)
    matched = 0
    skipped_dup = 0
    skipped_unmatched = 0

    for msg in messages:
        if not msg.from_email:
            skipped_unmatched += 1
            continue

        lead = db.scalar(
            select(Lead).where(
                Lead.tenant_id == account.tenant_id,
                Lead.email.ilike(msg.from_email),
            )
        )
        if lead is None:
            skipped_unmatched += 1
            continue

        already = db.scalar(
            select(Contact).where(
                Contact.lead_id == lead.id,
                Contact.external_id == msg.external_id,
            )
        )
        if already is not None:
            skipped_dup += 1
            continue

        db.add(
            Contact(
                lead_id=lead.id,
                type="email",
                direction="in",
                subject=msg.subject,
                body=msg.body,
                sent_at=msg.received_at,
                external_id=msg.external_id,
                thread_id=msg.thread_id,
            )
        )
        if lead.status in ("new", "contacted"):
            lead.status = "responded"
        matched += 1

    account.last_synced_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "fetched": fetched,
        "matched": matched,
        "skipped_duplicates": skipped_dup,
        "skipped_unmatched": skipped_unmatched,
    }
