import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.models.training import TrainingArea


class TrainingHoursCreate(BaseModel):
    trainee_id: uuid.UUID
    area: TrainingArea
    hours: float = Field(gt=0)
    entry_date: date
    teacher_id: uuid.UUID | None = None
    session_id: uuid.UUID | None = None
    note: str | None = None


class TrainingHoursRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    trainee_id: uuid.UUID
    area: TrainingArea
    hours: float
    entry_date: date
    teacher_id: uuid.UUID | None
    session_id: uuid.UUID | None
    note: str | None


class RequirementCreate(BaseModel):
    name: str
    area: TrainingArea
    required_hours: float = Field(ge=0)


class RequirementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    area: TrainingArea
    required_hours: float


class AreaProgress(BaseModel):
    area: str
    completed_hours: float
    required_hours: float
    progress: float | None


class TrainingDashboard(BaseModel):
    trainee_id: str
    total_completed: float
    total_required: float
    breakdown: list[AreaProgress]
