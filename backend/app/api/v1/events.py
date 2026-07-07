import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_staff
from app.db.session import get_db
from app.models.event import Event
from app.schemas.event import (
    EventCreate,
    EventRead,
    EventRegister,
    EventRegistrationRead,
    EventUpdate,
    PaymentConfirm,
)
from app.services import event as event_service
from app.services.event import (
    EventError,
    EventRegistrationRepository,
    EventRepository,
)
from app.services.member import MemberRepository

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=list[EventRead])
async def list_events(
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    return await EventRepository(db, current.tenant_id).list()


@router.post("", response_model=EventRead, status_code=status.HTTP_201_CREATED)
async def create_event(
    data: EventCreate,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    repo = EventRepository(db, current.tenant_id)
    event = repo.add(Event(**data.model_dump()))
    await db.commit()
    await db.refresh(event)
    return event


@router.patch("/{event_id}", response_model=EventRead)
async def update_event(
    event_id: uuid.UUID,
    data: EventUpdate,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    repo = EventRepository(db, current.tenant_id)
    event = await repo.get(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(event, field, value)
    await db.commit()
    await db.refresh(event)
    return event


@router.get("/{event_id}/registrations", response_model=list[EventRegistrationRead])
async def list_registrations(
    event_id: uuid.UUID,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    return await EventRegistrationRepository(db, current.tenant_id).for_event(event_id)


@router.post(
    "/{event_id}/register",
    response_model=EventRegistrationRead,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    event_id: uuid.UUID,
    data: EventRegister,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    event = await EventRepository(db, current.tenant_id).get(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    member = await MemberRepository(db, current.tenant_id).get(data.member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    try:
        return await event_service.register(db, current.tenant_id, event, member)
    except EventError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post(
    "/registrations/{registration_id}/pay",
    response_model=EventRegistrationRead,
)
async def confirm_payment(
    registration_id: uuid.UUID,
    data: PaymentConfirm,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    repo = EventRegistrationRepository(db, current.tenant_id)
    reg = await repo.get(registration_id)
    if reg is None:
        raise HTTPException(status_code=404, detail="Registration not found")
    return await event_service.confirm_payment(
        db, current.tenant_id, reg, data.amount_cents
    )


@router.delete(
    "/registrations/{registration_id}",
    response_model=EventRegistrationRead,
)
async def cancel_registration(
    registration_id: uuid.UUID,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    repo = EventRegistrationRepository(db, current.tenant_id)
    reg = await repo.get(registration_id)
    if reg is None:
        raise HTTPException(status_code=404, detail="Registration not found")
    return await event_service.cancel_registration(db, current.tenant_id, reg)
