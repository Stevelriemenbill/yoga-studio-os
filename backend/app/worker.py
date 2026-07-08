"""ARQ background worker.

Runs scheduled/deferred jobs against Redis:

* ``process_notifications`` – deliver due pending notifications (all tenants).
* ``run_automations`` – evaluate retention automation rules (all tenants).
* ``generate_insights`` – refresh care insights (all tenants).

Run with::

    arq app.worker.WorkerSettings

The cron schedule runs the batch jobs automatically; jobs can also be enqueued
on demand via :func:`enqueue_job` from the API.
"""

from arq import cron
from arq.connections import RedisSettings
from sqlalchemy import select

from app.core.config import settings
from app.core.events import publish
from app.db.session import AsyncSessionLocal
from app.models.tenant import Tenant
from app.services import ai as ai_service
from app.services import automation as automation_service
from app.services import notification as notification_service


async def _all_tenant_ids(db) -> list:
    result = await db.execute(select(Tenant.id))
    return list(result.scalars().all())


async def process_notifications(ctx: dict) -> dict:
    sent_total = 0
    async with AsyncSessionLocal() as db:
        for tenant_id in await _all_tenant_ids(db):
            sent = await notification_service.process_pending(db, tenant_id)
            sent_total += sent
            if sent:
                await publish(
                    tenant_id, "notifications.processed", {"sent": sent}
                )
    return {"sent": sent_total}


async def run_automations(ctx: dict) -> dict:
    total = 0
    async with AsyncSessionLocal() as db:
        for tenant_id in await _all_tenant_ids(db):
            result = await automation_service.run_all(db, tenant_id)
            total += result["total_enqueued"]
            if result["total_enqueued"]:
                await publish(tenant_id, "automations.ran", result)
    return {"total_enqueued": total}


async def generate_insights(ctx: dict) -> dict:
    count = 0
    async with AsyncSessionLocal() as db:
        for tenant_id in await _all_tenant_ids(db):
            insights = await ai_service.care_insights(db, tenant_id)
            count += len(insights)
            if insights:
                await publish(
                    tenant_id, "insights.generated", {"count": len(insights)}
                )
    return {"generated": count}


class WorkerSettings:
    functions = [process_notifications, run_automations, generate_insights]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    cron_jobs = [
        # Deliver notifications every minute.
        cron(process_notifications, minute=set(range(60))),
        # Evaluate automations hourly.
        cron(run_automations, minute={0}),
        # Refresh insights daily at 03:00.
        cron(generate_insights, hour={3}, minute={0}),
    ]
