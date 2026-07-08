"""Member self-service endpoints.

Everything here is scoped to the *authenticated member's own* record: the
member id is always derived from the login via :func:`get_current_member` and
never taken from client input. This lets members with a ``member``/``trainee``
login browse the schedule, book and cancel their own spots, view their bookings
and fetch their personal check-in QR pass — without exposing the staff-only
endpoints that trust a ``member_id`` from the request body.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_member, get_current_user
from app.core.events import publish
from app.db.session import get_db
from app.models.booking import BookingSource
from app.models.member import Member
from app.models.session import CourseSession
from app.schemas.booking import BookingRead
from app.schemas.checkin import MemberPassRead
from app.schemas.event import EventRead, EventRegistrationRead
from app.schemas.member import MemberRead
from app.schemas.participation import ParticipationHistory
from app.services import booking as booking_service
from app.services import event as event_service
from app.services import integrations as integrations_service
from app.services import participation as participation_service
from app.services import waitlist as waitlist_service
from app.services.booking import BookingError, BookingRepository
from app.services.checkin import member_qr_token
from app.services.event import (
    EventError,
    EventRegistrationRepository,
    EventRepository,
)

router = APIRouter(prefix="/me", tags=["member self-service"])


@router.get("/profile", response_model=MemberRead)
async def my_profile(
    member: Member = Depends(get_current_member),
):
    """The member profile linked to the current login."""
    return member


@router.get("/bookings", response_model=list[BookingRead])
async def my_bookings(
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    """All of the current member's bookings, newest session first."""
    return await BookingRepository(db, member.tenant_id).for_member(member.id)


@router.get("/participation", response_model=ParticipationHistory)
async def my_participation(
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    """Which sessions the member attended and their accumulated hours."""
    return await participation_service.participation_history(
        db, member.tenant_id, member.id
    )


async def _get_own_session(
    db: AsyncSession, tenant_id: uuid.UUID, session_id: uuid.UUID
) -> CourseSession:
    session = (
        await db.execute(
            select(CourseSession).where(
                CourseSession.tenant_id == tenant_id,
                CourseSession.id == session_id,
            )
        )
    ).scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post(
    "/bookings/{session_id}",
    response_model=BookingRead,
    status_code=status.HTTP_201_CREATED,
)
async def book_session(
    session_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    """Book the current member into a session (member id is derived, not sent)."""
    session = await _get_own_session(db, member.tenant_id, session_id)
    try:
        booking = await booking_service.create_booking(
            db, member.tenant_id, session, member, source=BookingSource.DIRECT
        )
    except BookingError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    await publish(
        member.tenant_id,
        "booking.created",
        {"session_id": str(session_id), "booking_id": str(booking.id)},
    )
    await integrations_service.dispatch_event(
        db,
        member.tenant_id,
        "booking.created",
        {"session_id": str(session_id), "booking_id": str(booking.id)},
    )
    return booking


@router.post("/bookings/{booking_id}/cancel", response_model=BookingRead)
async def cancel_my_booking(
    booking_id: uuid.UUID,
    reason: str | None = None,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    """Cancel one of the current member's own bookings.

    Ownership is enforced: a member can only cancel bookings that belong to
    their own member record (otherwise 404, to avoid leaking existence).
    """
    repo = BookingRepository(db, member.tenant_id)
    booking = await repo.get(booking_id)
    if booking is None or booking.member_id != member.id:
        raise HTTPException(status_code=404, detail="Booking not found")
    try:
        cancelled = await booking_service.cancel_booking(
            db, member.tenant_id, booking, reason
        )
    except BookingError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    # Free spot -> promote the next waitlisted member automatically.
    await waitlist_service.promote_next(db, member.tenant_id, booking.session_id)
    return cancelled


@router.get("/pass", response_model=MemberPassRead)
async def my_pass(
    member: Member = Depends(get_current_member),
):
    """The current member's signed QR check-in pass."""
    token = member_qr_token(member.tenant_id, member.id)
    return MemberPassRead(
        member_id=member.id,
        token=token,
        qr_payload=f"studioos://checkin?token={token}",
    )


@router.get("/events", response_model=list[EventRead])
async def my_events(
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    """Published events the current member can register for."""
    return await EventRepository(db, member.tenant_id).list_published()


@router.get("/events/registrations", response_model=list[EventRegistrationRead])
async def my_event_registrations(
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    """The current member's own event registrations."""
    return await EventRegistrationRepository(db, member.tenant_id).for_member(
        member.id
    )


@router.post(
    "/events/{event_id}/register",
    response_model=EventRegistrationRead,
    status_code=status.HTTP_201_CREATED,
)
async def register_for_event(
    event_id: uuid.UUID,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    """Register the current member for a published event (member id derived)."""
    event = await EventRepository(db, member.tenant_id).get(event_id)
    if event is None or not event.is_published:
        raise HTTPException(status_code=404, detail="Event not found")
    try:
        return await event_service.register(db, member.tenant_id, event, member)
    except EventError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post(
    "/events/registrations/{registration_id}/cancel",
    response_model=EventRegistrationRead,
)
async def cancel_my_event_registration(
    registration_id: uuid.UUID,
    member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    """Cancel one of the current member's own event registrations.

    Ownership is enforced: 404 if the registration is not the member's own.
    """
    repo = EventRegistrationRepository(db, member.tenant_id)
    reg = await repo.get(registration_id)
    if reg is None or reg.member_id != member.id:
        raise HTTPException(status_code=404, detail="Registration not found")
    return await event_service.cancel_registration(db, member.tenant_id, reg)
