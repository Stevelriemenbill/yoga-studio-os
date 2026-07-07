import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import GUID
from app.models.mixins import TenantMixin


class BookingStatus(str, enum.Enum):
    BOOKED = "booked"
    CANCELLED = "cancelled"
    ATTENDED = "attended"
    NO_SHOW = "no_show"


class BookingSource(str, enum.Enum):
    DIRECT = "direct"
    DROP_IN = "drop_in"
    WAITLIST = "waitlist"
    REBOOKED = "rebooked"


class Booking(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = "bookings"
    __table_args__ = (
        # A member can hold at most one active booking per session; enforced
        # in the service layer for status transitions. Unique on (session, member).
        UniqueConstraint("session_id", "member_id", name="uq_booking_session_member"),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("course_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("members.id", ondelete="CASCADE"), nullable=False, index=True
    )

    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus, native_enum=False, length=20),
        default=BookingStatus.BOOKED,
        nullable=False,
    )
    source: Mapped[BookingSource] = mapped_column(
        Enum(BookingSource, native_enum=False, length=20),
        default=BookingSource.DIRECT,
        nullable=False,
    )

    booked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancellation_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    session: Mapped["object"] = relationship(
        "CourseSession", back_populates="bookings", lazy="selectin"
    )
    member: Mapped["object"] = relationship("Member", lazy="selectin")
