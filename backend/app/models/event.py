import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import GUID
from app.models.mixins import TenantMixin


class EventType(str, enum.Enum):
    WORKSHOP = "workshop"
    RETREAT = "retreat"
    SPECIAL = "special"


class Event(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """Workshops, retreats and special events with distinct booking rules."""

    __tablename__ = "events"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    type: Mapped[EventType] = mapped_column(
        Enum(EventType, native_enum=False, length=20),
        default=EventType.WORKSHOP,
        nullable=False,
    )

    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)

    capacity: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    price_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Whether a deposit / prepayment is required to secure a spot.
    requires_deposit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deposit_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    teacher_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class EventRegistrationStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    WAITLISTED = "waitlisted"


class EventRegistration(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = "event_registrations"

    event_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("members.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[EventRegistrationStatus] = mapped_column(
        Enum(EventRegistrationStatus, native_enum=False, length=20),
        default=EventRegistrationStatus.PENDING,
        nullable=False,
    )
    amount_paid_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
