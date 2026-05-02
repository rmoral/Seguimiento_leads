from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    plan: Mapped[str] = mapped_column(String(40), default="free", nullable=False)

    # Reminder configuration (Phase 3)
    reminder_after_days: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    auto_reminders_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    users: Mapped[list["User"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")  # noqa: F821
    leads: Mapped[list["Lead"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")  # noqa: F821
    templates: Mapped[list["Template"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")  # noqa: F821
