"""Teilnahme-Historie einer Person.

Zeigt, an welchen Stunden jemand teilgenommen hat und wie viele Stunden dabei
zusammengekommen sind – ein Blick auf die eigene Praxis-Reise, nicht auf
Auslastung. Als 'besucht' zählt eine Buchung mit Status ATTENDED, ein Check-in
oder eine Anwesenheit (PRESENT/LATE).
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking, BookingStatus
from app.models.checkin import Attendance, AttendanceStatus, CheckIn
from app.models.course import Course
from app.models.session import CourseSession


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


async def _attended_session_ids(
    db: AsyncSession, tenant_id: uuid.UUID, member_id: uuid.UUID
) -> set[uuid.UUID]:
    """Session ids the member attended (booking attended / check-in / present)."""
    ids: set[uuid.UUID] = set()

    booked = (
        await db.execute(
            select(Booking.session_id).where(
                Booking.tenant_id == tenant_id,
                Booking.member_id == member_id,
                Booking.status == BookingStatus.ATTENDED,
            )
        )
    ).scalars().all()
    ids.update(booked)

    checked = (
        await db.execute(
            select(CheckIn.session_id).where(
                CheckIn.tenant_id == tenant_id,
                CheckIn.member_id == member_id,
                CheckIn.session_id.is_not(None),
            )
        )
    ).scalars().all()
    ids.update(checked)

    present = (
        await db.execute(
            select(Attendance.session_id).where(
                Attendance.tenant_id == tenant_id,
                Attendance.member_id == member_id,
                Attendance.status.in_(
                    [AttendanceStatus.PRESENT, AttendanceStatus.LATE]
                ),
            )
        )
    ).scalars().all()
    ids.update(present)

    return ids


async def participation_history(
    db: AsyncSession, tenant_id: uuid.UUID, member_id: uuid.UUID
) -> dict:
    """Attended sessions (newest first) plus accumulated-hours totals."""
    session_ids = await _attended_session_ids(db, tenant_id, member_id)
    if not session_ids:
        return {
            "total_sessions": 0,
            "total_hours": 0.0,
            "training_hours": 0.0,
            "entries": [],
        }

    rows = (
        await db.execute(
            select(
                CourseSession.id,
                CourseSession.course_id,
                CourseSession.starts_at,
                CourseSession.ends_at,
                Course.name,
                Course.counts_for_training,
            )
            .join(Course, Course.id == CourseSession.course_id)
            .where(CourseSession.id.in_(session_ids))
            .order_by(CourseSession.starts_at.desc())
        )
    ).all()

    entries: list[dict] = []
    total_hours = 0.0
    training_hours = 0.0
    for sid, _course_id, starts_at, ends_at, name, counts in rows:
        hours = (_aware(ends_at) - _aware(starts_at)).total_seconds() / 3600.0
        hours = round(hours, 2)
        total_hours += hours
        if counts:
            training_hours += hours
        entries.append(
            {
                "session_id": sid,
                "course_name": name,
                "starts_at": _aware(starts_at),
                "hours": hours,
                "counts_for_training": bool(counts),
            }
        )

    return {
        "total_sessions": len(entries),
        "total_hours": round(total_hours, 2),
        "training_hours": round(training_hours, 2),
        "entries": entries,
    }
