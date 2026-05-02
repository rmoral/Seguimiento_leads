"""add external_id/thread_id to contacts and last_synced_at to email_accounts

Revision ID: 0002_email_sync_fields
Revises: 0001_initial
Create Date: 2026-05-02

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_email_sync_fields"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("contacts", sa.Column("external_id", sa.String(255), nullable=True))
    op.add_column("contacts", sa.Column("thread_id", sa.String(255), nullable=True))
    op.create_unique_constraint(
        "uq_contact_external", "contacts", ["lead_id", "external_id"]
    )

    op.add_column(
        "email_accounts",
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("email_accounts", "last_synced_at")
    op.drop_constraint("uq_contact_external", "contacts", type_="unique")
    op.drop_column("contacts", "thread_id")
    op.drop_column("contacts", "external_id")
