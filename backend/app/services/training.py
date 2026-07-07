import csv
import io
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import TenantRepository
from app.models.training import (
    TrainingArea,
    TrainingHours,
    TrainingRequirement,
)


class TrainingHoursRepository(TenantRepository[TrainingHours]):
    model = TrainingHours

    async def for_trainee(self, trainee_id: uuid.UUID) -> list[TrainingHours]:
        result = await self.db.execute(
            self._base_query()
            .where(TrainingHours.trainee_id == trainee_id)
            .order_by(TrainingHours.entry_date)
        )
        return list(result.scalars().all())


class TrainingRequirementRepository(TenantRepository[TrainingRequirement]):
    model = TrainingRequirement


async def log_hours(
    db: AsyncSession, tenant_id: uuid.UUID, entry: TrainingHours
) -> TrainingHours:
    repo = TrainingHoursRepository(db, tenant_id)
    repo.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def dashboard(
    db: AsyncSession, tenant_id: uuid.UUID, trainee_id: uuid.UUID
) -> dict:
    """Aggregate logged hours per area vs. requirements."""
    logged_res = await db.execute(
        select(TrainingHours.area, func.sum(TrainingHours.hours))
        .where(
            TrainingHours.tenant_id == tenant_id,
            TrainingHours.trainee_id == trainee_id,
        )
        .group_by(TrainingHours.area)
    )
    logged = {area: float(total or 0) for area, total in logged_res.all()}

    req_res = await db.execute(
        select(TrainingRequirement.area, func.sum(TrainingRequirement.required_hours))
        .where(TrainingRequirement.tenant_id == tenant_id)
        .group_by(TrainingRequirement.area)
    )
    required = {area: float(total or 0) for area, total in req_res.all()}

    areas = set(logged) | set(required)
    breakdown = []
    for area in areas:
        done = logged.get(area, 0.0)
        req = required.get(area, 0.0)
        breakdown.append(
            {
                "area": area.value if isinstance(area, TrainingArea) else str(area),
                "completed_hours": round(done, 2),
                "required_hours": round(req, 2),
                "progress": round(done / req, 4) if req > 0 else None,
            }
        )
    breakdown.sort(key=lambda x: x["area"])
    return {
        "trainee_id": str(trainee_id),
        "total_completed": round(sum(logged.values()), 2),
        "total_required": round(sum(required.values()), 2),
        "breakdown": breakdown,
    }


async def export_csv(
    db: AsyncSession, tenant_id: uuid.UUID, trainee_id: uuid.UUID
) -> str:
    entries = await TrainingHoursRepository(db, tenant_id).for_trainee(trainee_id)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["date", "area", "hours", "teacher_id", "session_id", "note"])
    for e in entries:
        writer.writerow(
            [
                e.entry_date.isoformat(),
                e.area.value,
                e.hours,
                e.teacher_id or "",
                e.session_id or "",
                e.note or "",
            ]
        )
    return buffer.getvalue()
