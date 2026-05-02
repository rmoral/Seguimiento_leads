"""Celery app + Beat schedule.

Run with:
    celery -A app.celery_app.celery worker --loglevel=info
    celery -A app.celery_app.celery beat --loglevel=info
"""
from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery = Celery(
    "seguimiento_leads",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.sync", "app.tasks.reminders"],
)

celery.conf.update(
    timezone="UTC",
    enable_utc=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    result_expires=3600,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

celery.conf.beat_schedule = {
    # Pull new emails for every connected account every 15 minutes.
    "sync-all-inboxes": {
        "task": "app.tasks.sync.sync_all_inboxes",
        "schedule": crontab(minute="*/15"),
    },
    # Each morning, materialise pending follow-ups for leads that went silent.
    "create-followups-for-silent-leads": {
        "task": "app.tasks.reminders.create_followups_for_silent_leads",
        "schedule": crontab(hour=6, minute=0),
    },
    # An hour later, email each user a digest of their pending follow-ups.
    "send-daily-digest": {
        "task": "app.tasks.reminders.send_daily_digest",
        "schedule": crontab(hour=7, minute=0),
    },
}
