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
from app.models.tenant import Tenant

# Default check-in window (minutes) relative to session start. Per-studio values
# on the Tenant override these; the constants remain the fallback / defaults.
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


def _extract_token(raw: str) -> str:
    """Accept either a bare token or a full ``studioos://checkin?token=...``
    payload (what a camera scans from the QR code)."""
    raw = (raw or "").strip()
    if "token=" in raw:
        # Take everything after the first token= up to an & separator.
        raw = raw.split("token=", 1)[1].split("&", 1)[0]
    return raw


def verify_qr_token(tenant_id: uuid.UUID, token: str) -> uuid.UUID | None:
    token = _extract_token(token)
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

    async def pending(self) -> list[Attendance]:
        result = await self.db.execute(
            self._base_query()
            .where(Attendance.status == AttendanceStatus.PENDING)
            .order_by(Attendance.created_at.asc())
        )
        return list(result.scalars().all())


def _validate_window(
    session: CourseSession,
    now: datetime,
    opens_before: timedelta,
    closes_after: timedelta,
) -> None:
    starts = session.starts_at
    if starts.tzinfo is None:
        starts = starts.replace(tzinfo=UTC)
    opens = starts - opens_before
    closes = starts + closes_after
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
    requires_confirmation: bool = False,
) -> CheckIn:
    now = datetime.now(UTC)

    tenant = await db.get(Tenant, tenant_id)
    opens_before = (
        timedelta(minutes=tenant.checkin_opens_before)
        if tenant is not None
        else CHECKIN_OPENS_BEFORE
    )
    closes_after = (
        timedelta(minutes=tenant.checkin_closes_after)
        if tenant is not None
        else CHECKIN_CLOSES_AFTER
    )
    late_threshold = (
        timedelta(minutes=tenant.checkin_late_threshold)
        if tenant is not None
        else LATE_THRESHOLD
    )

    if enforce_window:
        _validate_window(session, now, opens_before, closes_after)

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

    if requires_confirmation:
        # Self check-in: record it but hold attendance until staff confirms.
        # Booking stays untouched so it does not count until confirmed.
        await _upsert_attendance(
            db, tenant_id, session.id, member.id, AttendanceStatus.PENDING
        )
    else:
        # Staff check-in: counts immediately.
        starts = session.starts_at
        if starts.tzinfo is None:
            starts = starts.replace(tzinfo=UTC)
        att_status = (
            AttendanceStatus.LATE
            if now > starts + late_threshold
            else AttendanceStatus.PRESENT
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


def _present_status(session: CourseSession, checked_in_at: datetime) -> AttendanceStatus:
    starts = session.starts_at
    if starts.tzinfo is None:
        starts = starts.replace(tzinfo=UTC)
    at = checked_in_at
    if at.tzinfo is None:
        at = at.replace(tzinfo=UTC)
    return (
        AttendanceStatus.LATE
        if at > starts + LATE_THRESHOLD
        else AttendanceStatus.PRESENT
    )


async def _latest_checkin(
    db: AsyncSession, tenant_id: uuid.UUID, session_id: uuid.UUID, member_id: uuid.UUID
) -> CheckIn | None:
    result = await db.execute(
        select(CheckIn)
        .where(
            CheckIn.tenant_id == tenant_id,
            CheckIn.session_id == session_id,
            CheckIn.member_id == member_id,
        )
        .order_by(CheckIn.checked_in_at.desc())
    )
    return result.scalars().first()


async def confirm_attendance(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    session: CourseSession,
    member_id: uuid.UUID,
    recorded_by: uuid.UUID,
) -> Attendance:
    """Staff confirms a pending self check-in: mark present/late and count it."""
    repo = AttendanceRepository(db, tenant_id)
    att = await repo.find(session.id, member_id)
    if att is None:
        raise CheckInError("No check-in to confirm for this member")
    if att.status != AttendanceStatus.PENDING:
        raise CheckInError("This attendance is not awaiting confirmation")

    checkin = await _latest_checkin(db, tenant_id, session.id, member_id)
    checked_in_at = checkin.checked_in_at if checkin else datetime.now(UTC)
    att.status = _present_status(session, checked_in_at)
    att.recorded_by = recorded_by

    booking = (
        await db.execute(
            select(Booking).where(
                Booking.tenant_id == tenant_id,
                Booking.session_id == session.id,
                Booking.member_id == member_id,
            )
        )
    ).scalar_one_or_none()
    if booking is not None:
        booking.status = BookingStatus.ATTENDED

    await db.commit()
    await db.refresh(att)
    return att


async def reject_attendance(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    session_id: uuid.UUID,
    member_id: uuid.UUID,
    recorded_by: uuid.UUID,
) -> Attendance:
    """Staff rejects a pending self check-in: mark absent (check-in log kept)."""
    repo = AttendanceRepository(db, tenant_id)
    att = await repo.find(session_id, member_id)
    if att is None:
        raise CheckInError("No check-in to reject for this member")
    if att.status != AttendanceStatus.PENDING:
        raise CheckInError("This attendance is not awaiting confirmation")

    att.status = AttendanceStatus.ABSENT
    att.recorded_by = recorded_by
    await db.commit()
    await db.refresh(att)
    return att
