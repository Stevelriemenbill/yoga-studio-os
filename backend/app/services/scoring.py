import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking, BookingStatus
from app.models.member import Member
from app.models.session import CourseSession


async def compute_reliability(
    db: AsyncSession, tenant_id: uuid.UUID, member_id: uuid.UUID
) -> float:
    """Statistical reliability score in [0, 1].

    Starts at 1.0 and is penalised by the rate of no-shows and late
    cancellations relative to total bookings. New members default high.
    """
    result = await db.execute(
        select(Booking.status, func.count())
        .where(
            Booking.tenant_id == tenant_id,
            Booking.member_id == member_id,
        )
        .group_by(Booking.status)
    )
    counts = {status: count for status, count in result.all()}

    total = sum(counts.values())
    if total == 0:
        return 1.0

    attended = counts.get(BookingStatus.ATTENDED, 0)
    no_show = counts.get(BookingStatus.NO_SHOW, 0)
    cancelled = counts.get(BookingStatus.CANCELLED, 0)

    # No-shows hurt the most; cancellations a little.
    penalty = (no_show * 1.0 + cancelled * 0.3) / total
    reward = attended / total * 0.1
    score = max(0.0, min(1.0, 1.0 - penalty + reward))
    return round(score, 4)


async def refresh_member_reliability(
    db: AsyncSession, tenant_id: uuid.UUID, member: Member
) -> Member:
    member.reliability_score = await compute_reliability(db, tenant_id, member.id)
    await db.commit()
    await db.refresh(member)
    return member


async def suggest_overbooking_allowance(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    session: CourseSession,
    policy: str = "conservative",
) -> int:
    """Suggest extra seats based on historical no-show rate for the course.

    policy: 'never' | 'conservative' | 'aggressive'. Studios stay in control.
    """
    if policy == "never":
        return 0

    result = await db.execute(
        select(Booking.status, func.count())
        .join(CourseSession, CourseSession.id == Booking.session_id)
        .where(
            Booking.tenant_id == tenant_id,
            CourseSession.course_id == session.course_id,
        )
        .group_by(Booking.status)
    )
    counts = {status: count for status, count in result.all()}
    total = sum(counts.values())
    if total < 20:
        # Not enough history to overbook responsibly.
        return 0

    no_show = counts.get(BookingStatus.NO_SHOW, 0)
    no_show_rate = no_show / total

    factor = 0.5 if policy == "conservative" else 1.0
    suggested = int(round(session.capacity * no_show_rate * factor))
    return max(0, suggested)
