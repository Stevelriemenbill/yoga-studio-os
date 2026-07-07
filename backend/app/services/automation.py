import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import TenantRepository
from app.models.automation import AutomationRule, AutomationTrigger
from app.models.booking import Booking
from app.models.member import Member
from app.services import notification as notification_service


class AutomationRepository(TenantRepository[AutomationRule]):
    model = AutomationRule

    async def active(self) -> list[AutomationRule]:
        result = await self.db.execute(
            self._base_query().where(AutomationRule.is_active.is_(True))
        )
        return list(result.scalars().all())


async def _last_activity(
    db: AsyncSession, tenant_id: uuid.UUID, member_id: uuid.UUID
) -> datetime | None:
    """Most recent booking time for a member (proxy for last activity)."""
    result = await db.execute(
        select(func.max(Booking.booked_at)).where(
            Booking.tenant_id == tenant_id,
            Booking.member_id == member_id,
        )
    )
    return result.scalar_one_or_none()


def render_template(template: str, member: Member) -> str:
    return template.replace("{first_name}", member.first_name).replace(
        "{last_name}", member.last_name
    )


async def run_inactivity_rule(
    db: AsyncSession, tenant_id: uuid.UUID, rule: AutomationRule
) -> int:
    """Enqueue a message for every member inactive for >= threshold_days.

    Retention ladder example: 7d reminder, 30d discount, 60d personal, 90d reactivation.
    """
    now = datetime.now(UTC)
    cutoff = now - timedelta(days=rule.threshold_days)

    members = (
        await db.execute(select(Member).where(Member.tenant_id == tenant_id))
    ).scalars().all()

    enqueued = 0
    for member in members:
        last = await _last_activity(db, tenant_id, member.id)
        # Never active, or last active before cutoff.
        is_inactive = last is None or last < cutoff
        if not is_inactive:
            continue
        await notification_service.enqueue(
            db,
            tenant_id,
            channel=rule.channel,
            body=render_template(rule.message_template, member),
            member_id=member.id,
            subject=rule.name,
            template=f"automation:{rule.id}",
        )
        enqueued += 1
    return enqueued


async def run_membership_expiring_rule(
    db: AsyncSession, tenant_id: uuid.UUID, rule: AutomationRule
) -> int:
    now = datetime.now(UTC).date()
    cutoff = now + timedelta(days=rule.threshold_days)
    members = (
        await db.execute(
            select(Member).where(
                Member.tenant_id == tenant_id,
                Member.membership_valid_until.is_not(None),
                Member.membership_valid_until <= cutoff,
                Member.membership_valid_until >= now,
            )
        )
    ).scalars().all()
    enqueued = 0
    for member in members:
        await notification_service.enqueue(
            db,
            tenant_id,
            channel=rule.channel,
            body=render_template(rule.message_template, member),
            member_id=member.id,
            subject=rule.name,
            template=f"automation:{rule.id}",
        )
        enqueued += 1
    return enqueued


async def run_rule(
    db: AsyncSession, tenant_id: uuid.UUID, rule: AutomationRule
) -> int:
    if rule.trigger == AutomationTrigger.INACTIVE_DAYS:
        return await run_inactivity_rule(db, tenant_id, rule)
    if rule.trigger == AutomationTrigger.MEMBERSHIP_EXPIRING:
        return await run_membership_expiring_rule(db, tenant_id, rule)
    # Event-driven triggers (after_booking, before_session, after_no_show) are
    # invoked from their respective domain services; nothing to batch here.
    return 0


async def run_all(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    """Evaluate all active batch rules for a tenant (invoked by scheduler)."""
    rules = await AutomationRepository(db, tenant_id).active()
    results = {}
    total = 0
    for rule in rules:
        count = await run_rule(db, tenant_id, rule)
        results[str(rule.id)] = count
        total += count
    return {"total_enqueued": total, "per_rule": results}
