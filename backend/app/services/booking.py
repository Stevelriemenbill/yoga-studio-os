import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import TenantRepository
from app.models.booking import Booking, BookingSource, BookingStatus
from app.models.member import Member
from app.models.session import CourseSession, SessionStatus


class BookingError(Exception):
    """Business error in the booking domain."""


class BookingRepository(TenantRepository[Booking]):
    model = Booking

    async def active_for_session(self, session_id: uuid.UUID) -> list[Booking]:
        result = await self.db.execute(
            self._base_query().where(
                Booking.session_id == session_id,
                Booking.status == BookingStatus.BOOKED,
            )
        )
        return list(result.scalars().all())

    async def find(
        self, session_id: uuid.UUID, member_id: uuid.UUID
    ) -> Booking | None:
        result = await self.db.execute(
            self._base_query().where(
                Booking.session_id == session_id,
                Booking.member_id == member_id,
            )
        )
        return result.scalar_one_or_none()


async def count_active_bookings(
    db: AsyncSession, tenant_id: uuid.UUID, session_id: uuid.UUID
) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(Booking)
        .where(
            Booking.tenant_id == tenant_id,
            Booking.session_id == session_id,
            Booking.status == BookingStatus.BOOKED,
        )
    )
    return int(result.scalar_one())


async def has_free_spot(
    db: AsyncSession, tenant_id: uuid.UUID, session: CourseSession
) -> bool:
    booked = await count_active_bookings(db, tenant_id, session.id)
    return booked < session.effective_capacity


async def create_booking(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    session: CourseSession,
    member: Member,
    source: BookingSource = BookingSource.DIRECT,
    *,
    commit: bool = True,
) -> Booking:
    if session.status != SessionStatus.SCHEDULED:
        raise BookingError("Session is not open for booking")

    repo = BookingRepository(db, tenant_id)
    existing = await repo.find(session.id, member.id)
    if existing is not None and existing.status == BookingStatus.BOOKED:
        raise BookingError("Member already booked for this session")

    if not await has_free_spot(db, tenant_id, session):
        raise BookingError("Session is full")

    if existing is not None:
        # Reactivate a previously cancelled booking.
        existing.status = BookingStatus.BOOKED
        existing.source = source
        existing.booked_at = datetime.now(UTC)
        existing.cancelled_at = None
        existing.cancellation_reason = None
        booking = existing
    else:
        booking = repo.add(
            Booking(
                session_id=session.id,
                member_id=member.id,
                status=BookingStatus.BOOKED,
                source=source,
                booked_at=datetime.now(UTC),
            )
        )

    if commit:
        await db.commit()
        await db.refresh(booking)
    return booking


async def cancel_booking(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    booking: Booking,
    reason: str | None = None,
    *,
    commit: bool = True,
) -> Booking:
    if booking.status != BookingStatus.BOOKED:
        raise BookingError("Booking is not active")
    booking.status = BookingStatus.CANCELLED
    booking.cancelled_at = datetime.now(UTC)
    booking.cancellation_reason = reason
    if commit:
        await db.commit()
        await db.refresh(booking)
    return booking


async def rebook(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    booking: Booking,
    new_session: CourseSession,
    member: Member,
) -> Booking:
    """Cancel the existing booking and create one on a new session."""
    if new_session.status != SessionStatus.SCHEDULED:
        raise BookingError("Target session is not open for booking")
    if not await has_free_spot(db, tenant_id, new_session):
        raise BookingError("Target session is full")

    await cancel_booking(db, tenant_id, booking, reason="rebooked", commit=False)
    new_booking = await create_booking(
        db, tenant_id, new_session, member, source=BookingSource.REBOOKED, commit=False
    )
    await db.commit()
    await db.refresh(new_booking)
    return new_booking
