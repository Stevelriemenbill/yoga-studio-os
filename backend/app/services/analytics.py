import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking, BookingStatus
from app.models.checkin import CheckIn
from app.models.member import Member
from app.models.session import CourseSession
from app.models.waitlist import WaitlistEntry


async def _count(db, stmt) -> int:
    result = await db.execute(stmt)
    return int(result.scalar_one() or 0)


async def studio_kpis(
    db: AsyncSession, tenant_id: uuid.UUID, start: datetime, end: datetime
) -> dict:
    """Core studio KPIs for a date range."""
    sessions = (
        await db.execute(
            select(CourseSession).where(
                CourseSession.tenant_id == tenant_id,
                CourseSession.starts_at >= start,
                CourseSession.starts_at < end,
            )
        )
    ).scalars().all()

    total_capacity = sum(s.effective_capacity for s in sessions)
    session_ids = [s.id for s in sessions]

    booked = 0
    no_shows = 0
    attended = 0
    cancellations = 0
    if session_ids:
        rows = (
            await db.execute(
                select(Booking.status, func.count())
                .where(
                    Booking.tenant_id == tenant_id,
                    Booking.session_id.in_(session_ids),
                )
                .group_by(Booking.status)
            )
        ).all()
        counts = {s: c for s, c in rows}
        booked = counts.get(BookingStatus.BOOKED, 0) + counts.get(
            BookingStatus.ATTENDED, 0
        )
        no_shows = counts.get(BookingStatus.NO_SHOW, 0)
        attended = counts.get(BookingStatus.ATTENDED, 0)
        cancellations = counts.get(BookingStatus.CANCELLED, 0)

    total_bookings = booked + no_shows
    check_ins = 0
    waitlist_total = 0
    new_members = await _count(
        db,
        select(func.count())
        .select_from(Member)
        .where(
            Member.tenant_id == tenant_id,
            Member.created_at >= start,
            Member.created_at < end,
        ),
    )
    if session_ids:
        check_ins = await _count(
            db,
            select(func.count())
            .select_from(CheckIn)
            .where(
                CheckIn.tenant_id == tenant_id,
                CheckIn.session_id.in_(session_ids),
            ),
        )
        waitlist_total = await _count(
            db,
            select(func.count())
            .select_from(WaitlistEntry)
            .where(
                WaitlistEntry.tenant_id == tenant_id,
                WaitlistEntry.session_id.in_(session_ids),
            ),
        )

    utilization = booked / total_capacity if total_capacity else 0.0
    no_show_rate = no_shows / total_bookings if total_bookings else 0.0
    avg_class_size = booked / len(sessions) if sessions else 0.0
    waitlist_ratio = waitlist_total / total_bookings if total_bookings else 0.0

    return {
        "sessions": len(sessions),
        "total_capacity": total_capacity,
        "bookings": booked,
        "utilization": round(utilization, 4),
        "no_show_rate": round(no_show_rate, 4),
        "cancellations": cancellations,
        "check_ins": check_ins,
        "attended": attended,
        "waitlist_ratio": round(waitlist_ratio, 4),
        "avg_class_size": round(avg_class_size, 2),
        "new_members": new_members,
    }


async def heatmap(
    db: AsyncSession, tenant_id: uuid.UUID, start: datetime, end: datetime
) -> list[dict]:
    """Occupancy heatmap by weekday x hour.

    Returns cells with utilization used to colour green/yellow/red.
    """
    sessions = (
        await db.execute(
            select(CourseSession).where(
                CourseSession.tenant_id == tenant_id,
                CourseSession.starts_at >= start,
                CourseSession.starts_at < end,
            )
        )
    ).scalars().all()

    cells: dict[tuple[int, int], dict] = {}
    for s in sessions:
        key = (s.starts_at.weekday(), s.starts_at.hour)
        booked = await _count(
            db,
            select(func.count())
            .select_from(Booking)
            .where(
                Booking.tenant_id == tenant_id,
                Booking.session_id == s.id,
                Booking.status.in_([BookingStatus.BOOKED, BookingStatus.ATTENDED]),
            ),
        )
        cell = cells.setdefault(key, {"booked": 0, "capacity": 0, "sessions": 0})
        cell["booked"] += booked
        cell["capacity"] += s.effective_capacity
        cell["sessions"] += 1

    result = []
    for (weekday, hour), cell in sorted(cells.items()):
        util = cell["booked"] / cell["capacity"] if cell["capacity"] else 0.0
        if util >= 0.85:
            level = "red"
        elif util >= 0.5:
            level = "yellow"
        else:
            level = "green"
        result.append(
            {
                "weekday": weekday,
                "hour": hour,
                "sessions": cell["sessions"],
                "utilization": round(util, 4),
                "level": level,
            }
        )
    return result


async def teacher_analytics(
    db: AsyncSession, tenant_id: uuid.UUID, start: datetime, end: datetime
) -> list[dict]:
    """Per-teacher utilization, no-shows, waitlist and unique returning members."""
    sessions = (
        await db.execute(
            select(CourseSession).where(
                CourseSession.tenant_id == tenant_id,
                CourseSession.starts_at >= start,
                CourseSession.starts_at < end,
                CourseSession.teacher_id.is_not(None),
            )
        )
    ).scalars().all()

    by_teacher: dict[uuid.UUID, dict] = {}
    for s in sessions:
        agg = by_teacher.setdefault(
            s.teacher_id,
            {
                "teacher_id": str(s.teacher_id),
                "sessions": 0,
                "capacity": 0,
                "booked": 0,
                "no_shows": 0,
                "waitlist": 0,
                "members": set(),
            },
        )
        agg["sessions"] += 1
        agg["capacity"] += s.effective_capacity

        rows = (
            await db.execute(
                select(Booking.member_id, Booking.status).where(
                    Booking.tenant_id == tenant_id, Booking.session_id == s.id
                )
            )
        ).all()
        for member_id, status_ in rows:
            if status_ in (BookingStatus.BOOKED, BookingStatus.ATTENDED):
                agg["booked"] += 1
                agg["members"].add(member_id)
            elif status_ == BookingStatus.NO_SHOW:
                agg["no_shows"] += 1
        agg["waitlist"] += await _count(
            db,
            select(func.count())
            .select_from(WaitlistEntry)
            .where(
                WaitlistEntry.tenant_id == tenant_id,
                WaitlistEntry.session_id == s.id,
            ),
        )

    result = []
    for agg in by_teacher.values():
        util = agg["booked"] / agg["capacity"] if agg["capacity"] else 0.0
        result.append(
            {
                "teacher_id": agg["teacher_id"],
                "sessions": agg["sessions"],
                "utilization": round(util, 4),
                "booked": agg["booked"],
                "no_shows": agg["no_shows"],
                "waitlist": agg["waitlist"],
                "unique_members": len(agg["members"]),
            }
        )
    result.sort(key=lambda x: -x["utilization"])
    return result


async def popular_courses(
    db: AsyncSession, tenant_id: uuid.UUID, start: datetime, end: datetime, limit: int = 5
) -> list[dict]:
    rows = (
        await db.execute(
            select(CourseSession.course_id, func.count(Booking.id))
            .join(Booking, Booking.session_id == CourseSession.id)
            .where(
                CourseSession.tenant_id == tenant_id,
                CourseSession.starts_at >= start,
                CourseSession.starts_at < end,
                Booking.status.in_([BookingStatus.BOOKED, BookingStatus.ATTENDED]),
            )
            .group_by(CourseSession.course_id)
            .order_by(func.count(Booking.id).desc())
            .limit(limit)
        )
    ).all()
    return [{"course_id": str(cid), "bookings": int(cnt)} for cid, cnt in rows]
