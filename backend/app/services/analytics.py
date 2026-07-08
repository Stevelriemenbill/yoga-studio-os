import uuid
from collections import defaultdict
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking, BookingStatus
from app.models.member import Member
from app.models.session import CourseSession


async def _count(db, stmt) -> int:
    result = await db.execute(stmt)
    return int(result.scalar_one() or 0)


async def community_pulse(
    db: AsyncSession, tenant_id: uuid.UUID, start: datetime, end: datetime
) -> dict:
    """Ein sanfter Puls der Gemeinschaft für einen Zeitraum.

    Bewusst menschzentriert: wie viele Menschen haben praktiziert, wie viele
    gemeinsame Stunden gab es, wer ist neu dazugekommen. Keine Auslastungs-
    oder Umsatzsteuerung – nur ein Gefühl dafür, wie es der Gemeinschaft geht.
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
    session_ids = [s.id for s in sessions]

    practicing_members: set = set()
    total_practices = 0
    if session_ids:
        rows = (
            await db.execute(
                select(Booking.member_id).where(
                    Booking.tenant_id == tenant_id,
                    Booking.session_id.in_(session_ids),
                    Booking.status == BookingStatus.ATTENDED,
                )
            )
        ).all()
        for (member_id,) in rows:
            practicing_members.add(member_id)
            total_practices += 1

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

    return {
        "sessions": len(sessions),
        "people_practicing": len(practicing_members),
        "total_practices": total_practices,
        "new_members": new_members,
    }


async def teacher_reach(
    db: AsyncSession, tenant_id: uuid.UUID, start: datetime, end: datetime
) -> list[dict]:
    """Wie viele Menschen begleitet eine Lehrkraft – und wie viele kommen wieder?

    Bewusst beziehungsorientiert: es geht um Nähe und Wiedersehen, nicht um
    Auslastung oder No-Show-Quoten.
    """
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
                "member_visits": defaultdict(int),
            },
        )
        agg["sessions"] += 1
        rows = (
            await db.execute(
                select(Booking.member_id).where(
                    Booking.tenant_id == tenant_id,
                    Booking.session_id == s.id,
                    Booking.status == BookingStatus.ATTENDED,
                )
            )
        ).all()
        for (member_id,) in rows:
            agg["member_visits"][member_id] += 1

    result = []
    for agg in by_teacher.values():
        visits = agg["member_visits"]
        unique = len(visits)
        returning = sum(1 for v in visits.values() if v >= 2)
        result.append(
            {
                "teacher_id": agg["teacher_id"],
                "sessions": agg["sessions"],
                "students_guided": unique,
                "returning_students": returning,
            }
        )
    result.sort(key=lambda x: -x["students_guided"])
    return result
