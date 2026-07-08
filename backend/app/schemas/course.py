import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.course import CourseLevel
from app.models.session import SessionStatus

#: Hard cap on how many sessions a single recurrence request may create,
#: to guard against runaway schedules.
MAX_RECURRENCE_SESSIONS = 200


# --- Room ---
class RoomCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    capacity: int = Field(default=20, ge=1)


class RoomUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    capacity: int | None = Field(default=None, ge=1)
    is_active: bool | None = None


class RoomRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    capacity: int
    is_active: bool


# --- Course ---
class CourseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    category: str | None = Field(default=None, max_length=120)
    level: CourseLevel = CourseLevel.ALL
    room_id: uuid.UUID | None = None
    teacher_id: uuid.UUID | None = None
    max_participants: int = Field(default=20, ge=1)
    min_participants: int = Field(default=1, ge=0)
    duration_minutes: int = Field(default=60, ge=1)
    counts_for_training: bool = False


class CourseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    category: str | None = Field(default=None, max_length=120)
    level: CourseLevel | None = None
    room_id: uuid.UUID | None = None
    teacher_id: uuid.UUID | None = None
    max_participants: int | None = Field(default=None, ge=1)
    min_participants: int | None = Field(default=None, ge=0)
    duration_minutes: int | None = Field(default=None, ge=1)
    is_active: bool | None = None
    counts_for_training: bool | None = None


class CourseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    category: str | None
    level: CourseLevel
    room_id: uuid.UUID | None
    teacher_id: uuid.UUID | None
    max_participants: int
    min_participants: int
    duration_minutes: int
    is_active: bool
    counts_for_training: bool


# --- Session ---
class SessionCreate(BaseModel):
    course_id: uuid.UUID
    starts_at: datetime
    teacher_id: uuid.UUID | None = None
    room_id: uuid.UUID | None = None
    capacity: int | None = Field(default=None, ge=1)


class RecurrenceSchedule(BaseModel):
    """Generate multiple sessions for a course via weekly recurrence.

    The series ends either on ``end_date`` (inclusive) OR after ``count``
    occurrences — exactly one of the two must be provided.
    """

    course_id: uuid.UUID
    #: Weekdays to schedule on, 0=Monday .. 6=Sunday.
    weekdays: list[int] = Field(min_length=1)
    start_time: time
    start_date: date
    end_date: date | None = None
    #: Number of occurrences to generate (alternative to ``end_date``).
    count: int | None = Field(default=None, ge=1, le=MAX_RECURRENCE_SESSIONS)
    exceptions: list[date] = Field(default_factory=list)

    @field_validator("weekdays")
    @classmethod
    def _validate_weekdays(cls, v: list[int]) -> list[int]:
        if any(d < 0 or d > 6 for d in v):
            raise ValueError("weekdays must be between 0 (Mon) and 6 (Sun)")
        return sorted(set(v))

    @model_validator(mode="after")
    def _validate_end(self) -> "RecurrenceSchedule":
        if (self.end_date is None) == (self.count is None):
            raise ValueError("provide exactly one of end_date or count")
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        return self


class SessionUpdate(BaseModel):
    starts_at: datetime | None = None
    teacher_id: uuid.UUID | None = None
    room_id: uuid.UUID | None = None
    capacity: int | None = Field(default=None, ge=1)
    overbooking_allowance: int | None = Field(default=None, ge=0)
    status: SessionStatus | None = None
    cancellation_reason: str | None = None


class SessionCancel(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class SessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    course_id: uuid.UUID
    teacher_id: uuid.UUID | None
    room_id: uuid.UUID | None
    starts_at: datetime
    ends_at: datetime
    capacity: int
    overbooking_allowance: int
    status: SessionStatus
    cancellation_reason: str | None = None


class SessionWithStats(SessionRead):
    booked_count: int = 0
    waitlist_count: int = 0
    available_spots: int = 0
