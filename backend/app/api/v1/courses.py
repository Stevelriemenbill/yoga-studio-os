import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_staff
from app.db.session import get_db
from app.models.booking import Booking, BookingStatus
from app.models.session import CourseSession
from app.models.waitlist import WaitlistEntry, WaitlistStatus
from app.schemas.course import (
    CourseCreate,
    CourseRead,
    CourseUpdate,
    RecurrenceSchedule,
    RoomCreate,
    RoomRead,
    SessionCreate,
    SessionRead,
    SessionUpdate,
    SessionWithStats,
)
from app.services import course as course_service
from app.services.course import (
    CourseRepository,
    RoomRepository,
    SessionRepository,
)

router = APIRouter(prefix="/courses", tags=["courses"])
rooms_router = APIRouter(prefix="/rooms", tags=["rooms"])
sessions_router = APIRouter(prefix="/sessions", tags=["sessions"])


# --- Rooms ---
@rooms_router.get("", response_model=list[RoomRead])
async def list_rooms(
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await RoomRepository(db, current.tenant_id).list()


@rooms_router.post("", response_model=RoomRead, status_code=status.HTTP_201_CREATED)
async def create_room(
    data: RoomCreate,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    return await course_service.create_room(db, current.tenant_id, data)


# --- Courses ---
@router.get("", response_model=list[CourseRead])
async def list_courses(
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await CourseRepository(db, current.tenant_id).list()


@router.post("", response_model=CourseRead, status_code=status.HTTP_201_CREATED)
async def create_course(
    data: CourseCreate,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    return await course_service.create_course(db, current.tenant_id, data)


@router.get("/{course_id}", response_model=CourseRead)
async def get_course(
    course_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    course = await CourseRepository(db, current.tenant_id).get(course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


@router.patch("/{course_id}", response_model=CourseRead)
async def update_course(
    course_id: uuid.UUID,
    data: CourseUpdate,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    course = await CourseRepository(db, current.tenant_id).get(course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return await course_service.update_course(db, current.tenant_id, course, data)


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    course_id: uuid.UUID,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    repo = CourseRepository(db, current.tenant_id)
    course = await repo.get(course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    await repo.delete(course)
    await db.commit()


@router.post(
    "/{course_id}/sessions",
    response_model=SessionRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_session_for_course(
    course_id: uuid.UUID,
    data: SessionCreate,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    course = await CourseRepository(db, current.tenant_id).get(course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    data.course_id = course_id
    return await course_service.create_session(db, current.tenant_id, course, data)


@router.post(
    "/{course_id}/schedule",
    response_model=list[SessionRead],
    status_code=status.HTTP_201_CREATED,
)
async def schedule_recurring(
    course_id: uuid.UUID,
    data: RecurrenceSchedule,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    course = await CourseRepository(db, current.tenant_id).get(course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    data.course_id = course_id
    return await course_service.schedule_recurring(db, current.tenant_id, course, data)


# --- Sessions (calendar) ---
@sessions_router.get("", response_model=list[SessionWithStats])
async def list_sessions(
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = SessionRepository(db, current.tenant_id)
    if start is None:
        start = datetime.now()
    if end is None:
        end = start + timedelta(days=7)
    sessions = await repo.list_range(start, end)
    return await _attach_stats(db, current.tenant_id, sessions)


@sessions_router.get("/{session_id}", response_model=SessionWithStats)
async def get_session(
    session_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await SessionRepository(db, current.tenant_id).get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    result = await _attach_stats(db, current.tenant_id, [session])
    return result[0]


@sessions_router.patch("/{session_id}", response_model=SessionRead)
async def update_session(
    session_id: uuid.UUID,
    data: SessionUpdate,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    session = await SessionRepository(db, current.tenant_id).get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return await course_service.update_session(db, session, data)


@sessions_router.post("/{session_id}/cancel", response_model=SessionRead)
async def cancel_session(
    session_id: uuid.UUID,
    reason: str | None = None,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    session = await SessionRepository(db, current.tenant_id).get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return await course_service.cancel_session(db, session, reason)


async def _attach_stats(
    db: AsyncSession, tenant_id: uuid.UUID, sessions: list[CourseSession]
) -> list[SessionWithStats]:
    result: list[SessionWithStats] = []
    for s in sessions:
        booked = await db.execute(
            select(func.count())
            .select_from(Booking)
            .where(
                Booking.tenant_id == tenant_id,
                Booking.session_id == s.id,
                Booking.status == BookingStatus.BOOKED,
            )
        )
        booked_count = int(booked.scalar_one())
        waitlisted = await db.execute(
            select(func.count())
            .select_from(WaitlistEntry)
            .where(
                WaitlistEntry.tenant_id == tenant_id,
                WaitlistEntry.session_id == s.id,
                WaitlistEntry.status == WaitlistStatus.WAITING,
            )
        )
        waitlist_count = int(waitlisted.scalar_one())
        item = SessionWithStats.model_validate(s)
        item.booked_count = booked_count
        item.waitlist_count = waitlist_count
        item.available_spots = max(0, s.effective_capacity - booked_count)
        result.append(item)
    return result
