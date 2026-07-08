import csv
import io
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import TenantRepository
from app.models.member import Member
from app.models.session import CourseSession
from app.models.training import (
    TrainingArea,
    TrainingCohort,
    TrainingEnrollment,
    TrainingHours,
    TrainingProgram,
    TrainingRequirement,
)
from app.services.participation import _attended_session_ids, _aware


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


# --- Programs / cohorts / enrollments ---
class ProgramRepository(TenantRepository[TrainingProgram]):
    model = TrainingProgram


class CohortRepository(TenantRepository[TrainingCohort]):
    model = TrainingCohort

    async def for_program(self, program_id: uuid.UUID) -> list[TrainingCohort]:
        result = await self.db.execute(
            self._base_query()
            .where(TrainingCohort.program_id == program_id)
            .order_by(TrainingCohort.start_date.desc())
        )
        return list(result.scalars().all())


class EnrollmentRepository(TenantRepository[TrainingEnrollment]):
    model = TrainingEnrollment

    async def for_cohort(self, cohort_id: uuid.UUID) -> list[TrainingEnrollment]:
        result = await self.db.execute(
            self._base_query().where(TrainingEnrollment.cohort_id == cohort_id)
        )
        return list(result.scalars().all())

    async def get_for_member(
        self, cohort_id: uuid.UUID, member_id: uuid.UUID
    ) -> TrainingEnrollment | None:
        result = await self.db.execute(
            self._base_query().where(
                TrainingEnrollment.cohort_id == cohort_id,
                TrainingEnrollment.member_id == member_id,
            )
        )
        return result.scalar_one_or_none()


async def _enrolled_count(
    db: AsyncSession, tenant_id: uuid.UUID, cohort_id: uuid.UUID
) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(TrainingEnrollment)
        .where(
            TrainingEnrollment.tenant_id == tenant_id,
            TrainingEnrollment.cohort_id == cohort_id,
        )
    )
    return int(result.scalar_one())


async def _member_names(
    db: AsyncSession, tenant_id: uuid.UUID, member_ids: list[uuid.UUID]
) -> dict[uuid.UUID, str]:
    if not member_ids:
        return {}
    rows = (
        await db.execute(
            select(Member.id, Member.first_name, Member.last_name).where(
                Member.tenant_id == tenant_id,
                Member.id.in_(member_ids),
            )
        )
    ).all()
    return {mid: f"{first} {last}".strip() for mid, first, last in rows}


async def _required_hours_for_program(
    db: AsyncSession, tenant_id: uuid.UUID, program_id: uuid.UUID
) -> float:
    result = await db.execute(
        select(func.sum(TrainingRequirement.required_hours)).where(
            TrainingRequirement.tenant_id == tenant_id,
            TrainingRequirement.program_id == program_id,
        )
    )
    return float(result.scalar_one() or 0.0)


async def _cohort_training_stats(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    cohort_id: uuid.UUID,
    member_id: uuid.UUID,
) -> tuple[int, float]:
    """Attended sessions and accumulated hours of a member within a cohort.

    Only counts sessions attached to the cohort (``cohort_id``) that the member
    actually attended (booking attended / check-in / present).
    """
    attended = await _attended_session_ids(db, tenant_id, member_id)
    if not attended:
        return 0, 0.0

    rows = (
        await db.execute(
            select(CourseSession.starts_at, CourseSession.ends_at).where(
                CourseSession.tenant_id == tenant_id,
                CourseSession.cohort_id == cohort_id,
                CourseSession.id.in_(attended),
            )
        )
    ).all()

    total_hours = 0.0
    for starts_at, ends_at in rows:
        total_hours += (_aware(ends_at) - _aware(starts_at)).total_seconds() / 3600.0
    return len(rows), round(total_hours, 2)


async def cohort_progress(
    db: AsyncSession, tenant_id: uuid.UUID, cohort: TrainingCohort
) -> dict:
    """Soll (required hours of the program) vs. ist (attended cohort hours)."""
    required = await _required_hours_for_program(db, tenant_id, cohort.program_id)
    enrollments = await EnrollmentRepository(db, tenant_id).for_cohort(cohort.id)
    names = await _member_names(
        db, tenant_id, [e.member_id for e in enrollments]
    )

    trainees = []
    for e in enrollments:
        sessions, hours = await _cohort_training_stats(
            db, tenant_id, cohort.id, e.member_id
        )
        trainees.append(
            {
                "member_id": e.member_id,
                "member_name": names.get(e.member_id),
                "status": e.status,
                "attended_sessions": sessions,
                "training_hours": hours,
            }
        )
    trainees.sort(key=lambda t: (t["member_name"] or "").lower())

    return {
        "cohort_id": cohort.id,
        "cohort_name": cohort.name,
        "required_hours": round(required, 2),
        "trainees": trainees,
    }


def default_enrolled_on(value: date | None) -> date:
    return value or datetime.now(UTC).date()
