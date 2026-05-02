from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class Contact(Base, TimestampMixin):
    """Each interaction (email sent/received, call, etc.) with a lead."""

    __tablename__ = "contacts"
    __table_args__ = (Index("ix_contacts_lead_sent", "lead_id", "sent_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)

    type: Mapped[str] = mapped_column(String(20), default="email", nullable=False)  # email, call, note
    direction: Mapped[str] = mapped_column(String(10), default="out", nullable=False)  # in, out
    subject: Mapped[str | None] = mapped_column(String(300))
    body: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    lead: Mapped["Lead"] = relationship(back_populates="contacts")  # noqa: F821
