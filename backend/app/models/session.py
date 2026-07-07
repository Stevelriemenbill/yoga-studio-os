import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import GUID
from app.models.mixins import TenantMixin


class SessionStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class CourseSession(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """A concrete, bookable occurrence of a course at a specific time."""

    __tablename__ = "course_sessions"

    course_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    teacher_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    room_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("rooms.id", ondelete="SET NULL"), nullable=True
    )

    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Effective capacity for this occurrence (may differ from course default,
    # e.g. via overbooking allowance).
    capacity: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    # Extra seats allowed on top of capacity due to overbooking policy.
    overbooking_allowance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus, native_enum=False, length=20),
        default=SessionStatus.SCHEDULED,
        nullable=False,
    )
    cancellation_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    course: Mapped["object"] = relationship(
        "Course", back_populates="sessions", lazy="selectin"
    )
    bookings: Mapped[list["object"]] = relationship(
        "Booking",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def effective_capacity(self) -> int:
        return self.capacity + self.overbooking_allowance
