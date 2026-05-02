"""Daily follow-up generation + digest delivery."""
from __future__ import annotations

from app.celery_app import celery
from app.core.database import SessionLocal
from app.services.reminders import (
    create_followups_for_silent_leads,
    send_daily_digest,
)


@celery.task(name="app.tasks.reminders.create_followups_for_silent_leads")
def create_followups_for_silent_leads_task() -> dict:
    db = SessionLocal()
    try:
        created = create_followups_for_silent_leads(db)
        return {"created": created}
    finally:
        db.close()


@celery.task(name="app.tasks.reminders.send_daily_digest")
def send_daily_digest_task() -> dict:
    db = SessionLocal()
    try:
        result = send_daily_digest(db)
        return {
            "users_notified": result.users_notified,
            "users_skipped_no_account": result.users_skipped_no_account,
            "users_skipped_no_followups": result.users_skipped_no_followups,
            "users_skipped_already_sent_today": result.users_skipped_already_sent_today,
        }
    finally:
        db.close()
