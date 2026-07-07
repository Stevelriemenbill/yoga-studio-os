import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import TenantRepository
from app.models.event import (
    Event,
    EventRegistration,
    EventRegistrationStatus,
)
from app.models.member import Member


class EventError(Exception):
    pass


class EventRepository(TenantRepository[Event]):
    model = Event


class EventRegistrationRepository(TenantRepository[EventRegistration]):
    model = EventRegistration

    async def for_event(self, event_id: uuid.UUID) -> list[EventRegistration]:
        result = await self.db.execute(
            self._base_query().where(EventRegistration.event_id == event_id)
        )
        return list(result.scalars().all())

    async def find(
        self, event_id: uuid.UUID, member_id: uuid.UUID
    ) -> EventRegistration | None:
        result = await self.db.execute(
            self._base_query().where(
                EventRegistration.event_id == event_id,
                EventRegistration.member_id == member_id,
            )
        )
        return result.scalar_one_or_none()


async def _confirmed_count(
    db: AsyncSession, tenant_id: uuid.UUID, event_id: uuid.UUID
) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(EventRegistration)
        .where(
            EventRegistration.tenant_id == tenant_id,
            EventRegistration.event_id == event_id,
            EventRegistration.status == EventRegistrationStatus.CONFIRMED,
        )
    )
    return int(result.scalar_one())


async def register(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    event: Event,
    member: Member,
) -> EventRegistration:
    repo = EventRegistrationRepository(db, tenant_id)
    existing = await repo.find(event.id, member.id)
    if existing is not None and existing.status in {
        EventRegistrationStatus.PENDING,
        EventRegistrationStatus.CONFIRMED,
        EventRegistrationStatus.WAITLISTED,
    }:
        raise EventError("Member already registered for this event")

    confirmed = await _confirmed_count(db, tenant_id, event.id)
    full = confirmed >= event.capacity

    # Distinct booking rule: deposit required -> stays PENDING until paid.
    if full:
        status = EventRegistrationStatus.WAITLISTED
    elif event.requires_deposit:
        status = EventRegistrationStatus.PENDING
    else:
        status = EventRegistrationStatus.CONFIRMED

    reg = repo.add(
        EventRegistration(
            event_id=event.id,
            member_id=member.id,
            status=status,
        )
    )
    await db.commit()
    await db.refresh(reg)
    return reg


async def confirm_payment(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    reg: EventRegistration,
    amount_cents: int,
) -> EventRegistration:
    reg.amount_paid_cents += amount_cents
    if reg.status == EventRegistrationStatus.PENDING:
        reg.status = EventRegistrationStatus.CONFIRMED
    await db.commit()
    await db.refresh(reg)
    return reg


async def cancel_registration(
    db: AsyncSession, tenant_id: uuid.UUID, reg: EventRegistration
) -> EventRegistration:
    event_id = reg.event_id
    reg.status = EventRegistrationStatus.CANCELLED
    await db.commit()

    # Promote first waitlisted registration if a spot opened.
    repo = EventRegistrationRepository(db, tenant_id)
    regs = await repo.for_event(event_id)
    waitlisted = [
        r for r in regs if r.status == EventRegistrationStatus.WAITLISTED
    ]
    event = await EventRepository(db, tenant_id).get(event_id)
    if event and waitlisted:
        confirmed = await _confirmed_count(db, tenant_id, event_id)
        if confirmed < event.capacity:
            promote = min(waitlisted, key=lambda r: r.created_at)
            promote.status = (
                EventRegistrationStatus.PENDING
                if event.requires_deposit
                else EventRegistrationStatus.CONFIRMED
            )
            await db.commit()

    await db.refresh(reg)
    return reg
