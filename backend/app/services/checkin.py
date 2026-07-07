import hashlib
import hmac
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.repository import TenantRepository
from app.models.booking import Booking, BookingStatus
from app.models.checkin import (
    Attendance,
    AttendanceStatus,
    CheckIn,
    CheckInMethod,
)
from app.models.member import Member
from app.models.session import CourseSession

# Anti-abuse: allowed check-in window relative to session start.
CHECKIN_OPENS_BEFORE = timedelta(minutes=30)
CHECKIN_CLOSES_AFTER = timedelta(minutes=15)
LATE_THRESHOLD = timedelta(minutes=5)


class CheckInError(Exception):
    pass


def member_qr_token(tenant_id: uuid.UUID, member_id: uuid.UUID) -> str:
    """Deterministic signed token embedded in a member's QR / wallet pass.

    Format: <member_id>.<hmac>. The HMAC binds the token to the server secret
    so it cannot be forged. Rotating SECRET_KEY invalidates all passes.
    """
    msg = f"{tenant_id}:{member_id}".encode()
    sig = hmac.new(settings.SECRET_KEY.encode(), msg, hashlib.sha256).hexdigest()[:32]
    return f"{member_id}.{sig}"


def verify_qr_token(tenant_id: uuid.UUID, token: str) -> uuid.UUID | None:
    try:
        member_part, sig = token.split(".", 1)
        member_id = uuid.UUID(member_part)
    except (ValueError, AttributeError):
        return None
    expected = member_qr_token(tenant_id, member_id).split(".", 1)[1]
    if not hmac.compare_digest(sig, expected):
        return None
    return member_id


class CheckInRepository(TenantRepository[CheckIn]):
    model = CheckIn

    async def exists_for(
        self, member_id: uuid.UUID, session_id: uuid.UUID
    ) -> bool:
        result = await self.db.execute(
            self._base_query().where(
                CheckIn.member_id == member_id, CheckIn.session_id == session_id
            )
        )
        return result.scalar_one_or_none() is not None


class AttendanceRepository(TenantRepository[Attendance]):
    model = Attendance

    async def for_session(self, session_id: uuid.UUID) -> list[Attendance]:
        result = await self.db.execute(
            self._base_query().where(Attendance.session_id == session_id)
        )
        return list(result.scalars().all())

    async def find(
        self, session_id: uuid.UUID, member_id: uuid.UUID
    ) -> Attendance | None:
        result = await self.db.execute(
            self._base_query().where(
                Attendance.session_id == session_id,
                Attendance.member_id == member_id,
            )
        )
        return result.scalar_one_or_none()


def _validate_window(session: CourseSession, now: datetime) -> None:
    starts = session.starts_at
    if starts.tzinfo is None:
        starts = starts.replace(tzinfo=UTC)
    opens = starts - CHECKIN_OPENS_BEFORE
    closes = starts + CHECKIN_CLOSES_AFTER
    if now < opens:
        raise CheckInError("Check-in not yet open for this session")
    if now > closes:
        raise CheckInError("Check-in window has closed")


async def check_in(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    session: CourseSession,
    member: Member,
    method: CheckInMethod = CheckInMethod.QR,
    device_id: str | None = None,
    *,
    enforce_window: bool = True,
) -> CheckIn:
    now = datetime.now(UTC)
    if enforce_window:
        _validate_window(session, now)

    checkin_repo = CheckInRepository(db, tenant_id)
    # Anti-abuse: only one check-in per member per session.
    if await checkin_repo.exists_for(member.id, session.id):
        raise CheckInError("Already checked in for this session")

    # Link to the member's booking if present.
    booking_res = await db.execute(
        select(Booking).where(
            Booking.tenant_id == tenant_id,
            Booking.session_id == session.id,
            Booking.member_id == member.id,
        )
    )
    booking = booking_res.scalar_one_or_none()

    entry = checkin_repo.add(
        CheckIn(
            member_id=member.id,
            session_id=session.id,
            booking_id=booking.id if booking else None,
            checked_in_at=now,
            method=method,
            device_id=device_id,
        )
    )

    # Reflect attendance + booking status.
    starts = session.starts_at
    if starts.tzinfo is None:
        starts = starts.replace(tzinfo=UTC)
    att_status = (
        AttendanceStatus.LATE if now > starts + LATE_THRESHOLD else AttendanceStatus.PRESENT
    )
    await _upsert_attendance(db, tenant_id, session.id, member.id, att_status)
    if booking is not None:
        booking.status = BookingStatus.ATTENDED

    await db.commit()
    await db.refresh(entry)
    return entry


async def _upsert_attendance(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    session_id: uuid.UUID,
    member_id: uuid.UUID,
    status: AttendanceStatus,
    recorded_by: uuid.UUID | None = None,
) -> Attendance:
    repo = AttendanceRepository(db, tenant_id)
    existing = await repo.find(session_id, member_id)
    if existing is not None:
        existing.status = status
        if recorded_by:
            existing.recorded_by = recorded_by
        return existing
    return repo.add(
        Attendance(
            session_id=session_id,
            member_id=member_id,
            status=status,
            recorded_by=recorded_by,
        )
    )


async def set_attendance(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    session_id: uuid.UUID,
    member_id: uuid.UUID,
    status: AttendanceStatus,
    recorded_by: uuid.UUID | None = None,
) -> Attendance:
    att = await _upsert_attendance(
        db, tenant_id, session_id, member_id, status, recorded_by
    )
    await db.commit()
    await db.refresh(att)
    return att
