import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import GUID
from app.models.mixins import TenantMixin


class WaitlistStatus(str, enum.Enum):
    WAITING = "waiting"
    OFFERED = "offered"  # a spot was offered, awaiting response
    ACCEPTED = "accepted"  # converted to a booking
    DECLINED = "declined"
    EXPIRED = "expired"  # did not respond in time
    CANCELLED = "cancelled"


class WaitlistEntry(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = "waitlist_entries"

    session_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("course_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("members.id", ondelete="CASCADE"), nullable=False, index=True
    )

    status: Mapped[WaitlistStatus] = mapped_column(
        Enum(WaitlistStatus, native_enum=False, length=20),
        default=WaitlistStatus.WAITING,
        nullable=False,
    )

    # Manual priority boost (higher = earlier). Combined with score + timestamp.
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Snapshot of member reliability at join time for ranking.
    score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    offered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    offer_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    member: Mapped["object"] = relationship("Member", lazy="selectin")
