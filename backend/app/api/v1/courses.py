import uuid
from datetime import datetime, timedelta

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_staff
from app.core.config import settings
from app.db.session import get_db
from app.models.booking import Booking, BookingStatus
from app.models.course import CourseAttachment
from app.models.session import CourseSession
from app.models.waitlist import WaitlistEntry, WaitlistStatus
from app.schemas.course import (
    CourseAttachmentRead,
    CourseCreate,
    CourseRead,
    CourseUpdate,
    RecurrenceSchedule,
    RoomCreate,
    RoomRead,
    SeriesActionResult,
    SeriesUpdate,
    SessionCancel,
    SessionCreate,
    SessionRead,
    SessionUpdate,
    SessionWithStats,
)
from app.services import course as course_service
from app.services import storage
from app.services.course import (
    CourseAttachmentRepository,
    CourseRepository,
    RoomRepository,
    SessionRepository,
)

router = APIRouter(prefix="/courses", tags=["courses"])
rooms_router = APIRouter(prefix="/rooms", tags=["rooms"])
sessions_router = APIRouter(prefix="/sessions", tags=["sessions"])
series_router = APIRouter(prefix="/series", tags=["series"])


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


# --- Course attachments ---
def _attachment_read(att: CourseAttachment) -> CourseAttachmentRead:
    read = CourseAttachmentRead.model_validate(att)
    read.url = storage.course_file_url(att.tenant_id, att.course_id, att.stored_name)
    return read


@router.get("/{course_id}/attachments", response_model=list[CourseAttachmentRead])
async def list_course_attachments(
    course_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if await CourseRepository(db, current.tenant_id).get(course_id) is None:
        raise HTTPException(status_code=404, detail="Course not found")
    atts = await CourseAttachmentRepository(db, current.tenant_id).for_course(course_id)
    return [_attachment_read(a) for a in atts]


@router.post(
    "/{course_id}/attachments",
    response_model=CourseAttachmentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_course_attachment(
    course_id: uuid.UUID,
    file: UploadFile = File(...),
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    if await CourseRepository(db, current.tenant_id).get(course_id) is None:
        raise HTTPException(status_code=404, detail="Course not found")

    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large")
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    stored_name, _rel = storage.save_course_file(
        current.tenant_id, course_id, file.filename or "upload", content
    )
    att = CourseAttachmentRepository(db, current.tenant_id).add(
        CourseAttachment(
            course_id=course_id,
            filename=file.filename or "upload",
            stored_name=stored_name,
            content_type=file.content_type,
            size_bytes=len(content),
        )
    )
    await db.commit()
    await db.refresh(att)
    return _attachment_read(att)


@router.delete(
    "/{course_id}/attachments/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_course_attachment(
    course_id: uuid.UUID,
    attachment_id: uuid.UUID,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    repo = CourseAttachmentRepository(db, current.tenant_id)
    att = await repo.get(attachment_id)
    if att is None or att.course_id != course_id:
        raise HTTPException(status_code=404, detail="Attachment not found")
    storage.delete_course_file(current.tenant_id, course_id, att.stored_name)
    await repo.delete(att)
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
    data: SessionCancel | None = None,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    session = await SessionRepository(db, current.tenant_id).get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    reason = data.reason if data else None
    return await course_service.cancel_session(
        db, session, reason, tenant_id=current.tenant_id
    )


# --- Series (recurrence) ---
@series_router.get("/{series_id}", response_model=list[SessionWithStats])
async def list_series_sessions(
    series_id: uuid.UUID,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    sessions = await SessionRepository(db, current.tenant_id).list_for_series(series_id)
    if not sessions:
        raise HTTPException(status_code=404, detail="Series not found")
    return await _attach_stats(db, current.tenant_id, sessions)


@series_router.patch("/{series_id}", response_model=SeriesActionResult)
async def update_series(
    series_id: uuid.UUID,
    data: SeriesUpdate,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    existing = await SessionRepository(db, current.tenant_id).list_for_series(series_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Series not found")
    updated = await course_service.update_series(
        db, current.tenant_id, series_id, data
    )
    return SeriesActionResult(series_id=series_id, affected=len(updated))


@series_router.post("/{series_id}/cancel", response_model=SeriesActionResult)
async def cancel_series(
    series_id: uuid.UUID,
    data: SessionCancel | None = None,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    existing = await SessionRepository(db, current.tenant_id).list_for_series(series_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Series not found")
    reason = data.reason if data else None
    affected = await course_service.cancel_series(
        db, current.tenant_id, series_id, reason
    )
    return SeriesActionResult(series_id=series_id, affected=affected)


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
