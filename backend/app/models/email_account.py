from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin


class EmailAccount(Base, TimestampMixin):
    """Connected email account (Gmail, Outlook, SMTP). Tokens stored encrypted in Phase 2."""

    __tablename__ = "email_accounts"
    __table_args__ = (UniqueConstraint("tenant_id", "email", name="uq_email_account"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    provider: Mapped[str] = mapped_column(String(20), nullable=False)  # gmail, outlook, smtp
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    oauth_tokens: Mapped[str | None] = mapped_column(Text)  # encrypted JSON, populated in Phase 2
