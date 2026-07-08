import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import GUID
from app.models.mixins import TenantMixin


class CheckInMethod(str, enum.Enum):
    QR = "qr"
    NFC = "nfc"
    MANUAL = "manual"
    KIOSK = "kiosk"


class CheckIn(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = "check_ins"

    member_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("members.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("course_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("bookings.id", ondelete="SET NULL"), nullable=True
    )

    checked_in_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    method: Mapped[CheckInMethod] = mapped_column(
        Enum(CheckInMethod, native_enum=False, length=20),
        default=CheckInMethod.QR,
        nullable=False,
    )
    # Device/kiosk identifier for device-binding anti-abuse.
    device_id: Mapped[str | None] = mapped_column(String(120), nullable=True)


class AttendanceStatus(str, enum.Enum):
    PENDING = "pending"  # Selbst-Check-in, wartet auf Bestätigung
    PRESENT = "present"  # Anwesend
    ABSENT = "absent"  # Nicht erschienen
    EXCUSED = "excused"  # Entschuldigt
    LATE = "late"  # Verspätet


class Attendance(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = "attendance"

    session_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("course_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("members.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[AttendanceStatus] = mapped_column(
        Enum(AttendanceStatus, native_enum=False, length=20),
        default=AttendanceStatus.PRESENT,
        nullable=False,
    )
    recorded_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
