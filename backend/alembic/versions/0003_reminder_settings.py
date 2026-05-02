"""Phase 3: tenant reminder settings + user last_digest_sent_at

Revision ID: 0003_reminder_settings
Revises: 0002_email_sync_fields
Create Date: 2026-05-02

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_reminder_settings"
down_revision: Union[str, None] = "0002_email_sync_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("reminder_after_days", sa.Integer(), nullable=False, server_default="7"),
    )
    op.add_column(
        "tenants",
        sa.Column(
            "auto_reminders_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.add_column(
        "users",
        sa.Column("last_digest_sent_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "last_digest_sent_at")
    op.drop_column("tenants", "auto_reminders_enabled")
    op.drop_column("tenants", "reminder_after_days")
