import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_staff
from app.db.session import get_db
from app.models.training import (
    TrainingCohort,
    TrainingEnrollment,
    TrainingHours,
    TrainingProgram,
    TrainingRequirement,
)
from app.schemas.training import (
    CohortCreate,
    CohortProgress,
    CohortRead,
    CohortUpdate,
    EnrollmentCreate,
    EnrollmentRead,
    EnrollmentUpdate,
    ProgramCreate,
    ProgramRead,
    ProgramUpdate,
    RequirementCreate,
    RequirementRead,
    TrainingDashboard,
    TrainingHoursCreate,
    TrainingHoursRead,
)
from app.services import training as training_service
from app.services.training import (
    CohortRepository,
    EnrollmentRepository,
    ProgramRepository,
    TrainingHoursRepository,
    TrainingRequirementRepository,
)

router = APIRouter(prefix="/training", tags=["training"])


@router.post("/hours", response_model=TrainingHoursRead, status_code=status.HTTP_201_CREATED)
async def log_hours(
    data: TrainingHoursCreate,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    entry = TrainingHours(**data.model_dump())
    return await training_service.log_hours(db, current.tenant_id, entry)


@router.get("/hours/{trainee_id}", response_model=list[TrainingHoursRead])
async def list_hours(
    trainee_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await TrainingHoursRepository(db, current.tenant_id).for_trainee(trainee_id)


@router.get("/dashboard/{trainee_id}", response_model=TrainingDashboard)
async def dashboard(
    trainee_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await training_service.dashboard(db, current.tenant_id, trainee_id)


@router.get("/export/{trainee_id}.csv", response_class=PlainTextResponse)
async def export_csv(
    trainee_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    csv_data = await training_service.export_csv(db, current.tenant_id, trainee_id)
    return PlainTextResponse(
        csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=training_{trainee_id}.csv"
        },
    )


@router.post(
    "/requirements", response_model=RequirementRead, status_code=status.HTTP_201_CREATED
)
async def create_requirement(
    data: RequirementCreate,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    repo = TrainingRequirementRepository(db, current.tenant_id)
    req = repo.add(TrainingRequirement(**data.model_dump()))
    await db.commit()
    await db.refresh(req)
    return req


@router.get("/requirements", response_model=list[RequirementRead])
async def list_requirements(
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await TrainingRequirementRepository(db, current.tenant_id).list()


# --- Programs ---
@router.post(
    "/programs", response_model=ProgramRead, status_code=status.HTTP_201_CREATED
)
async def create_program(
    data: ProgramCreate,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    repo = ProgramRepository(db, current.tenant_id)
    program = repo.add(TrainingProgram(**data.model_dump()))
    await db.commit()
    await db.refresh(program)
    return program


@router.get("/programs", response_model=list[ProgramRead])
async def list_programs(
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await ProgramRepository(db, current.tenant_id).list()


@router.patch("/programs/{program_id}", response_model=ProgramRead)
async def update_program(
    program_id: uuid.UUID,
    data: ProgramUpdate,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    repo = ProgramRepository(db, current.tenant_id)
    program = await repo.get(program_id)
    if program is None:
        raise HTTPException(status_code=404, detail="Program not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(program, field, value)
    await db.commit()
    await db.refresh(program)
    return program


# --- Cohorts ---
@router.post(
    "/cohorts", response_model=CohortRead, status_code=status.HTTP_201_CREATED
)
async def create_cohort(
    data: CohortCreate,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    program = await ProgramRepository(db, current.tenant_id).get(data.program_id)
    if program is None:
        raise HTTPException(status_code=404, detail="Program not found")
    cohort = CohortRepository(db, current.tenant_id).add(
        TrainingCohort(**data.model_dump())
    )
    await db.commit()
    await db.refresh(cohort)
    return CohortRead(**_cohort_dict(cohort, enrolled_count=0))


@router.get("/cohorts", response_model=list[CohortRead])
async def list_cohorts(
    program_id: uuid.UUID | None = None,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = CohortRepository(db, current.tenant_id)
    cohorts = (
        await repo.for_program(program_id)
        if program_id is not None
        else await repo.list()
    )
    result = []
    for c in cohorts:
        count = await training_service._enrolled_count(db, current.tenant_id, c.id)
        result.append(CohortRead(**_cohort_dict(c, enrolled_count=count)))
    return result


@router.patch("/cohorts/{cohort_id}", response_model=CohortRead)
async def update_cohort(
    cohort_id: uuid.UUID,
    data: CohortUpdate,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    repo = CohortRepository(db, current.tenant_id)
    cohort = await repo.get(cohort_id)
    if cohort is None:
        raise HTTPException(status_code=404, detail="Cohort not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(cohort, field, value)
    await db.commit()
    await db.refresh(cohort)
    count = await training_service._enrolled_count(db, current.tenant_id, cohort.id)
    return CohortRead(**_cohort_dict(cohort, enrolled_count=count))


@router.get("/cohorts/{cohort_id}/progress", response_model=CohortProgress)
async def cohort_progress(
    cohort_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cohort = await CohortRepository(db, current.tenant_id).get(cohort_id)
    if cohort is None:
        raise HTTPException(status_code=404, detail="Cohort not found")
    return await training_service.cohort_progress(db, current.tenant_id, cohort)


# --- Enrollments ---
@router.post(
    "/cohorts/{cohort_id}/enrollments",
    response_model=EnrollmentRead,
    status_code=status.HTTP_201_CREATED,
)
async def enroll_member(
    cohort_id: uuid.UUID,
    data: EnrollmentCreate,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    repo = EnrollmentRepository(db, current.tenant_id)
    cohort = await CohortRepository(db, current.tenant_id).get(cohort_id)
    if cohort is None:
        raise HTTPException(status_code=404, detail="Cohort not found")
    existing = await repo.get_for_member(cohort_id, data.member_id)
    if existing is not None:
        raise HTTPException(
            status_code=409, detail="Member already enrolled in this cohort"
        )
    enrollment = repo.add(
        TrainingEnrollment(
            cohort_id=cohort_id,
            member_id=data.member_id,
            enrolled_on=training_service.default_enrolled_on(data.enrolled_on),
            status=data.status,
        )
    )
    await db.commit()
    await db.refresh(enrollment)
    return enrollment


@router.get("/cohorts/{cohort_id}/enrollments", response_model=list[EnrollmentRead])
async def list_enrollments(
    cohort_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    enrollments = await EnrollmentRepository(db, current.tenant_id).for_cohort(
        cohort_id
    )
    names = await training_service._member_names(
        db, current.tenant_id, [e.member_id for e in enrollments]
    )
    return [
        EnrollmentRead(
            id=e.id,
            cohort_id=e.cohort_id,
            member_id=e.member_id,
            enrolled_on=e.enrolled_on,
            status=e.status,
            member_name=names.get(e.member_id),
        )
        for e in enrollments
    ]


@router.patch("/enrollments/{enrollment_id}", response_model=EnrollmentRead)
async def update_enrollment(
    enrollment_id: uuid.UUID,
    data: EnrollmentUpdate,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    repo = EnrollmentRepository(db, current.tenant_id)
    enrollment = await repo.get(enrollment_id)
    if enrollment is None:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    enrollment.status = data.status
    await db.commit()
    await db.refresh(enrollment)
    return enrollment


@router.delete(
    "/enrollments/{enrollment_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_enrollment(
    enrollment_id: uuid.UUID,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    repo = EnrollmentRepository(db, current.tenant_id)
    enrollment = await repo.get(enrollment_id)
    if enrollment is None:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    await repo.delete(enrollment)
    await db.commit()


def _cohort_dict(cohort: TrainingCohort, *, enrolled_count: int) -> dict:
    return {
        "id": cohort.id,
        "program_id": cohort.program_id,
        "name": cohort.name,
        "start_date": cohort.start_date,
        "end_date": cohort.end_date,
        "status": cohort.status,
        "enrolled_count": enrolled_count,
    }
