import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import TenantRepository
from app.models.booking import BookingSource
from app.models.member import Member
from app.models.session import CourseSession, SessionStatus
from app.models.waitlist import WaitlistEntry, WaitlistStatus
from app.services import booking as booking_service

# How long an offered spot is held before moving to the next person.
DEFAULT_OFFER_MINUTES = 15


class WaitlistError(Exception):
    pass


class WaitlistRepository(TenantRepository[WaitlistEntry]):
    model = WaitlistEntry

    async def waiting_for_session(
        self, session_id: uuid.UUID
    ) -> list[WaitlistEntry]:
        result = await self.db.execute(
            self._base_query().where(
                WaitlistEntry.session_id == session_id,
                WaitlistEntry.status == WaitlistStatus.WAITING,
            )
        )
        return list(result.scalars().all())

    async def find(
        self, session_id: uuid.UUID, member_id: uuid.UUID
    ) -> WaitlistEntry | None:
        result = await self.db.execute(
            self._base_query().where(
                WaitlistEntry.session_id == session_id,
                WaitlistEntry.member_id == member_id,
            )
        )
        return result.scalar_one_or_none()


def rank_key(entry: WaitlistEntry) -> tuple:
    """Ranking: higher priority first, then higher reliability, then earlier join.

    Not a simple FIFO — reliability score and manual priority take precedence.
    """
    return (-entry.priority, -entry.score, entry.joined_at)


async def join_waitlist(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    session: CourseSession,
    member: Member,
    priority: int = 0,
) -> WaitlistEntry:
    if session.status != SessionStatus.SCHEDULED:
        raise WaitlistError("Session is not open")

    repo = WaitlistRepository(db, tenant_id)
    existing = await repo.find(session.id, member.id)
    if existing is not None and existing.status in {
        WaitlistStatus.WAITING,
        WaitlistStatus.OFFERED,
    }:
        raise WaitlistError("Member already on the waitlist")

    entry = repo.add(
        WaitlistEntry(
            session_id=session.id,
            member_id=member.id,
            status=WaitlistStatus.WAITING,
            priority=priority,
            score=member.reliability_score,
            joined_at=datetime.now(UTC),
        )
    )
    await db.commit()
    await db.refresh(entry)
    return entry


async def next_candidate(
    db: AsyncSession, tenant_id: uuid.UUID, session_id: uuid.UUID
) -> WaitlistEntry | None:
    entries = await WaitlistRepository(db, tenant_id).waiting_for_session(session_id)
    if not entries:
        return None
    entries.sort(key=rank_key)
    return entries[0]


async def offer_spot(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    entry: WaitlistEntry,
    offer_minutes: int = DEFAULT_OFFER_MINUTES,
) -> WaitlistEntry:
    now = datetime.now(UTC)
    entry.status = WaitlistStatus.OFFERED
    entry.offered_at = now
    entry.offer_expires_at = now + timedelta(minutes=offer_minutes)
    await db.commit()
    await db.refresh(entry)
    return entry


async def accept_offer(
    db: AsyncSession, tenant_id: uuid.UUID, entry: WaitlistEntry
) -> WaitlistEntry:
    if entry.status != WaitlistStatus.OFFERED:
        raise WaitlistError("No active offer to accept")

    session = await _get_session(db, tenant_id, entry.session_id)
    member = await _get_member(db, tenant_id, entry.member_id)
    if session is None or member is None:
        raise WaitlistError("Session or member missing")

    await booking_service.create_booking(
        db, tenant_id, session, member, source=BookingSource.WAITLIST, commit=False
    )
    entry.status = WaitlistStatus.ACCEPTED
    entry.responded_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(entry)
    return entry


async def decline_offer(
    db: AsyncSession, tenant_id: uuid.UUID, entry: WaitlistEntry
) -> WaitlistEntry:
    entry.status = WaitlistStatus.DECLINED
    entry.responded_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(entry)
    return entry


async def process_expired_offers(
    db: AsyncSession, tenant_id: uuid.UUID
) -> list[WaitlistEntry]:
    """Mark expired offers and return them (caller re-offers to next candidate)."""
    now = datetime.now(UTC)
    result = await db.execute(
        select(WaitlistEntry).where(
            WaitlistEntry.tenant_id == tenant_id,
            WaitlistEntry.status == WaitlistStatus.OFFERED,
            WaitlistEntry.offer_expires_at < now,
        )
    )
    expired = list(result.scalars().all())
    for entry in expired:
        entry.status = WaitlistStatus.EXPIRED
    await db.commit()
    return expired


async def promote_next(
    db: AsyncSession, tenant_id: uuid.UUID, session_id: uuid.UUID
) -> WaitlistEntry | None:
    """Offer the freed spot to the highest-ranked waiting member.

    In a production system the offer would be sent via WhatsApp/Push/E-Mail
    and only converted to a booking on acceptance. Here we create the offer.
    """
    session = await _get_session(db, tenant_id, session_id)
    if session is None:
        return None
    if not await booking_service.has_free_spot(db, tenant_id, session):
        return None
    candidate = await next_candidate(db, tenant_id, session_id)
    if candidate is None:
        return None
    return await offer_spot(db, tenant_id, candidate)


async def recommend_alternatives(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    session: CourseSession,
    *,
    window_days: int = 7,
    limit: int = 5,
) -> list[CourseSession]:
    """Dynamic waitlist: suggest nearby sessions with free spots.

    Prefers same course, then same teacher, within the time window.
    """
    start = session.starts_at - timedelta(days=window_days)
    end = session.starts_at + timedelta(days=window_days)
    result = await db.execute(
        select(CourseSession).where(
            CourseSession.tenant_id == tenant_id,
            CourseSession.id != session.id,
            CourseSession.status == SessionStatus.SCHEDULED,
            CourseSession.starts_at >= start,
            CourseSession.starts_at <= end,
        )
    )
    candidates = list(result.scalars().all())

    scored: list[tuple[int, CourseSession]] = []
    for cand in candidates:
        if not await booking_service.has_free_spot(db, tenant_id, cand):
            continue
        score = 0
        if cand.course_id == session.course_id:
            score += 3
        if cand.teacher_id and cand.teacher_id == session.teacher_id:
            score += 2
        # Closer in time is better.
        delta_hours = abs((cand.starts_at - session.starts_at).total_seconds()) / 3600
        score += max(0, 3 - int(delta_hours // 24))
        scored.append((score, cand))

    scored.sort(key=lambda x: (-x[0], x[1].starts_at))
    return [c for _, c in scored[:limit]]


async def _get_session(
    db: AsyncSession, tenant_id: uuid.UUID, session_id: uuid.UUID
) -> CourseSession | None:
    result = await db.execute(
        select(CourseSession).where(
            CourseSession.tenant_id == tenant_id, CourseSession.id == session_id
        )
    )
    return result.scalar_one_or_none()


async def _get_member(
    db: AsyncSession, tenant_id: uuid.UUID, member_id: uuid.UUID
) -> Member | None:
    result = await db.execute(
        select(Member).where(Member.tenant_id == tenant_id, Member.id == member_id)
    )
    return result.scalar_one_or_none()
