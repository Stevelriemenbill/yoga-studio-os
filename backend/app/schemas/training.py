import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.models.training import (
    CohortStatus,
    EnrollmentStatus,
    TrainingArea,
)


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
    program_id: uuid.UUID | None = None


class RequirementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    area: TrainingArea
    required_hours: float
    program_id: uuid.UUID | None = None


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


# --- Programs ---
class ProgramCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    duration_months: int = Field(default=24, ge=1)


class ProgramUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    duration_months: int | None = Field(default=None, ge=1)
    is_active: bool | None = None


class ProgramRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    duration_months: int
    is_active: bool


# --- Cohorts ---
class CohortCreate(BaseModel):
    program_id: uuid.UUID
    name: str = Field(min_length=1, max_length=255)
    start_date: date
    end_date: date | None = None
    status: CohortStatus = CohortStatus.PLANNED


class CohortUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    start_date: date | None = None
    end_date: date | None = None
    status: CohortStatus | None = None


class CohortRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    program_id: uuid.UUID
    name: str
    start_date: date
    end_date: date | None
    status: CohortStatus
    enrolled_count: int = 0


# --- Enrollments ---
class EnrollmentCreate(BaseModel):
    member_id: uuid.UUID
    enrolled_on: date | None = None
    status: EnrollmentStatus = EnrollmentStatus.ACTIVE


class EnrollmentUpdate(BaseModel):
    status: EnrollmentStatus


class EnrollmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cohort_id: uuid.UUID
    member_id: uuid.UUID
    enrolled_on: date
    status: EnrollmentStatus
    member_name: str | None = None


# --- Cohort progress (soll vs ist) ---
class TraineeProgress(BaseModel):
    member_id: uuid.UUID
    member_name: str | None
    status: EnrollmentStatus
    attended_sessions: int
    training_hours: float


class CohortProgress(BaseModel):
    cohort_id: uuid.UUID
    cohort_name: str
    required_hours: float
    trainees: list[TraineeProgress]
