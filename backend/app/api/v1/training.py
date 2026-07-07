import uuid

from fastapi import APIRouter, Depends, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_staff
from app.db.session import get_db
from app.models.training import TrainingHours, TrainingRequirement
from app.schemas.training import (
    RequirementCreate,
    RequirementRead,
    TrainingDashboard,
    TrainingHoursCreate,
    TrainingHoursRead,
)
from app.services import training as training_service
from app.services.training import (
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
