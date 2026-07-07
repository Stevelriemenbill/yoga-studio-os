import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user
from app.core.events import publish
from app.db.session import get_db
from app.models.booking import BookingSource
from app.models.member import Member
from app.models.session import CourseSession
from app.schemas.booking import (
    BookingCreate,
    BookingRead,
    BookingRebook,
    SessionRef,
    WaitlistJoin,
    WaitlistRead,
)
from app.services import booking as booking_service
from app.services import integrations as integrations_service
from app.services import waitlist as waitlist_service
from app.services.booking import BookingError, BookingRepository
from app.services.waitlist import WaitlistError, WaitlistRepository

router = APIRouter(prefix="/bookings", tags=["bookings"])
waitlist_router = APIRouter(prefix="/waitlist", tags=["waitlist"])


async def _load_session_member(
    db: AsyncSession, tenant_id: uuid.UUID, session_id: uuid.UUID, member_id: uuid.UUID
) -> tuple[CourseSession, Member]:
    session = (
        await db.execute(
            select(CourseSession).where(
                CourseSession.tenant_id == tenant_id, CourseSession.id == session_id
            )
        )
    ).scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    member = (
        await db.execute(
            select(Member).where(Member.tenant_id == tenant_id, Member.id == member_id)
        )
    ).scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return session, member


@router.post("", response_model=BookingRead, status_code=status.HTTP_201_CREATED)
async def create_booking(
    data: BookingCreate,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session, member = await _load_session_member(
        db, current.tenant_id, data.session_id, data.member_id
    )
    source = BookingSource.DROP_IN if data.drop_in else BookingSource.DIRECT
    try:
        booking = await booking_service.create_booking(
            db, current.tenant_id, session, member, source=source
        )
    except BookingError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await publish(
        current.tenant_id,
        "booking.created",
        {"session_id": str(data.session_id), "booking_id": str(booking.id)},
    )
    await integrations_service.dispatch_event(
        db,
        current.tenant_id,
        "booking.created",
        {"session_id": str(data.session_id), "booking_id": str(booking.id)},
    )
    return booking


@router.get("/session/{session_id}", response_model=list[BookingRead])
async def list_bookings_for_session(
    session_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await BookingRepository(db, current.tenant_id).active_for_session(session_id)


@router.post("/{booking_id}/cancel", response_model=BookingRead)
async def cancel_booking(
    booking_id: uuid.UUID,
    reason: str | None = None,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = BookingRepository(db, current.tenant_id)
    booking = await repo.get(booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    try:
        cancelled = await booking_service.cancel_booking(
            db, current.tenant_id, booking, reason
        )
    except BookingError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    # Free spot -> promote the next waitlisted member automatically.
    await waitlist_service.promote_next(db, current.tenant_id, booking.session_id)
    return cancelled


@router.post("/{booking_id}/rebook", response_model=BookingRead)
async def rebook_booking(
    booking_id: uuid.UUID,
    data: BookingRebook,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = BookingRepository(db, current.tenant_id)
    booking = await repo.get(booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    session, member = await _load_session_member(
        db, current.tenant_id, data.new_session_id, booking.member_id
    )
    old_session_id = booking.session_id
    try:
        new_booking = await booking_service.rebook(
            db, current.tenant_id, booking, session, member
        )
    except BookingError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await waitlist_service.promote_next(db, current.tenant_id, old_session_id)
    return new_booking


# --- Waitlist ---
@waitlist_router.post("", response_model=WaitlistRead, status_code=status.HTTP_201_CREATED)
async def join_waitlist(
    data: WaitlistJoin,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session, member = await _load_session_member(
        db, current.tenant_id, data.session_id, data.member_id
    )
    try:
        return await waitlist_service.join_waitlist(
            db, current.tenant_id, session, member, priority=data.priority
        )
    except WaitlistError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@waitlist_router.get("/session/{session_id}", response_model=list[WaitlistRead])
async def list_waitlist(
    session_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    entries = await WaitlistRepository(db, current.tenant_id).waiting_for_session(
        session_id
    )
    entries.sort(key=waitlist_service.rank_key)
    return entries


@waitlist_router.post("/{entry_id}/accept", response_model=WaitlistRead)
async def accept_offer(
    entry_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    entry = await WaitlistRepository(db, current.tenant_id).get(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Waitlist entry not found")
    try:
        return await waitlist_service.accept_offer(db, current.tenant_id, entry)
    except (WaitlistError, BookingError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@waitlist_router.post("/{entry_id}/decline", response_model=WaitlistRead)
async def decline_offer(
    entry_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    entry = await WaitlistRepository(db, current.tenant_id).get(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Waitlist entry not found")
    result = await waitlist_service.decline_offer(db, current.tenant_id, entry)
    # Offer the freed slot to the next candidate.
    await waitlist_service.promote_next(db, current.tenant_id, entry.session_id)
    return result


@waitlist_router.get(
    "/session/{session_id}/alternatives", response_model=list[SessionRef]
)
async def waitlist_alternatives(
    session_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = (
        await db.execute(
            select(CourseSession).where(
                CourseSession.tenant_id == current.tenant_id,
                CourseSession.id == session_id,
            )
        )
    ).scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return await waitlist_service.recommend_alternatives(db, current.tenant_id, session)
