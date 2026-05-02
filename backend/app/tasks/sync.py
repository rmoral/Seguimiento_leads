"""Periodic inbox sync task."""
from __future__ import annotations

from app.celery_app import celery
from app.core.database import SessionLocal
from app.services.reminders import sync_all_inboxes


@celery.task(name="app.tasks.sync.sync_all_inboxes")
def sync_all_inboxes_task() -> dict:
    db = SessionLocal()
    try:
        result = sync_all_inboxes(db)
        return {
            "accounts_processed": result.accounts_processed,
            "accounts_failed": result.accounts_failed,
            "total_matched": result.total_matched,
        }
    finally:
        db.close()
