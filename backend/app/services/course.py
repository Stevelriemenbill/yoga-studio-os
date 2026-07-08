import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import TenantRepository
from app.models.course import Course, CourseAttachment, Room
from app.models.session import CourseSession, SessionStatus
from app.schemas.course import (
    MAX_RECURRENCE_SESSIONS,
    CourseCreate,
    CourseUpdate,
    RecurrenceSchedule,
    RoomCreate,
    SessionCreate,
    SessionUpdate,
)
from app.services.recurrence import RecurrenceRule, expand_recurrence


class RoomRepository(TenantRepository[Room]):
    model = Room


class CourseRepository(TenantRepository[Course]):
    model = Course


class CourseAttachmentRepository(TenantRepository[CourseAttachment]):
    model = CourseAttachment

    async def for_course(self, course_id: uuid.UUID) -> list[CourseAttachment]:
        result = await self.db.execute(
            self._base_query()
            .where(CourseAttachment.course_id == course_id)
            .order_by(CourseAttachment.created_at)
        )
        return list(result.scalars().all())


class SessionRepository(TenantRepository[CourseSession]):
    model = CourseSession

    async def list_range(
        self, start: datetime, end: datetime
    ) -> list[CourseSession]:
        result = await self.db.execute(
            self._base_query()
            .where(CourseSession.starts_at >= start)
            .where(CourseSession.starts_at < end)
            .order_by(CourseSession.starts_at)
        )
        return list(result.scalars().all())

    async def list_for_course(self, course_id: uuid.UUID) -> list[CourseSession]:
        result = await self.db.execute(
            self._base_query()
            .where(CourseSession.course_id == course_id)
            .order_by(CourseSession.starts_at)
        )
        return list(result.scalars().all())


# --- Room operations ---
async def create_room(db: AsyncSession, tenant_id: uuid.UUID, data: RoomCreate) -> Room:
    repo = RoomRepository(db, tenant_id)
    room = repo.add(Room(name=data.name, capacity=data.capacity))
    await db.commit()
    await db.refresh(room)
    return room


# --- Course operations ---
async def create_course(
    db: AsyncSession, tenant_id: uuid.UUID, data: CourseCreate
) -> Course:
    repo = CourseRepository(db, tenant_id)
    course = repo.add(Course(**data.model_dump()))
    await db.commit()
    await db.refresh(course)
    return course


async def update_course(
    db: AsyncSession, tenant_id: uuid.UUID, course: Course, data: CourseUpdate
) -> Course:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(course, field, value)
    await db.commit()
    await db.refresh(course)
    return course


# --- Session operations ---
async def _resolve_capacity(
    course: Course, override: int | None
) -> int:
    if override is not None:
        return override
    return course.max_participants


async def create_session(
    db: AsyncSession, tenant_id: uuid.UUID, course: Course, data: SessionCreate
) -> CourseSession:
    repo = SessionRepository(db, tenant_id)
    capacity = data.capacity if data.capacity is not None else course.max_participants
    session = repo.add(
        CourseSession(
            course_id=course.id,
            teacher_id=data.teacher_id or course.teacher_id,
            room_id=data.room_id or course.room_id,
            starts_at=data.starts_at,
            ends_at=data.starts_at + timedelta(minutes=course.duration_minutes),
            capacity=capacity,
            location=data.location,
            is_online=data.is_online,
            online_url=data.online_url,
        )
    )
    await db.commit()
    await db.refresh(session)
    return session


async def schedule_recurring(
    db: AsyncSession, tenant_id: uuid.UUID, course: Course, data: RecurrenceSchedule
) -> list[CourseSession]:
    rule = RecurrenceRule(
        weekdays=data.weekdays,
        start_time=data.start_time,
        start_date=data.start_date,
        end_date=data.end_date,
        count=data.count,
        exceptions=set(data.exceptions),
    )
    starts = expand_recurrence(rule)
    # Bound total work regardless of which end condition is used.
    starts = starts[:MAX_RECURRENCE_SESSIONS]
    repo = SessionRepository(db, tenant_id)

    # Avoid duplicates: fetch existing start times for this course.
    existing = {s.starts_at.replace(tzinfo=None) for s in await repo.list_for_course(course.id)}

    created: list[CourseSession] = []
    for start in starts:
        if start.replace(tzinfo=None) in existing:
            continue
        session = repo.add(
            CourseSession(
                course_id=course.id,
                teacher_id=course.teacher_id,
                room_id=course.room_id,
                starts_at=start,
                ends_at=start + timedelta(minutes=course.duration_minutes),
                capacity=course.max_participants,
            )
        )
        created.append(session)

    await db.commit()
    for s in created:
        await db.refresh(s)
    return created


async def update_session(
    db: AsyncSession, session: CourseSession, data: SessionUpdate
) -> CourseSession:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(session, field, value)
    await db.commit()
    await db.refresh(session)
    return session


async def cancel_session(
    db: AsyncSession,
    session: CourseSession,
    reason: str | None,
    *,
    tenant_id: uuid.UUID | None = None,
    notify: bool = True,
) -> CourseSession:
    from app.models.booking import Booking, BookingStatus
    from app.services import notification as notification_service

    tid = tenant_id if tenant_id is not None else session.tenant_id

    session.status = SessionStatus.CANCELLED
    session.cancellation_reason = reason

    # Notify booked members before their bookings are cancelled.
    if notify:
        await notification_service.notify_session_cancelled(
            db, tid, session, reason=reason
        )

    # Cancel every active booking for this session.
    bookings = (
        (
            await db.execute(
                select(Booking).where(
                    Booking.tenant_id == tid,
                    Booking.session_id == session.id,
                    Booking.status == BookingStatus.BOOKED,
                )
            )
        )
        .scalars()
        .all()
    )
    for booking in bookings:
        booking.status = BookingStatus.CANCELLED

    await db.commit()
    await db.refresh(session)
    return session
