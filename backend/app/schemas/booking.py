import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.booking import BookingSource, BookingStatus
from app.models.waitlist import WaitlistStatus


class BookingCreate(BaseModel):
    session_id: uuid.UUID
    member_id: uuid.UUID
    drop_in: bool = False


class BookingRebook(BaseModel):
    new_session_id: uuid.UUID


class BookingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    member_id: uuid.UUID
    status: BookingStatus
    source: BookingSource
    booked_at: datetime | None
    cancelled_at: datetime | None


class WaitlistJoin(BaseModel):
    session_id: uuid.UUID
    member_id: uuid.UUID
    priority: int = 0


class WaitlistRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    member_id: uuid.UUID
    status: WaitlistStatus
    priority: int
    score: float
    joined_at: datetime
    offered_at: datetime | None
    offer_expires_at: datetime | None


class SessionRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    course_id: uuid.UUID
    starts_at: datetime
    teacher_id: uuid.UUID | None
