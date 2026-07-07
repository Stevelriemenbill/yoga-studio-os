import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.event import EventRegistrationStatus, EventType


class EventCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    type: EventType = EventType.WORKSHOP
    starts_at: datetime
    ends_at: datetime
    location: str | None = None
    capacity: int = Field(default=20, ge=1)
    price_cents: int = Field(default=0, ge=0)
    requires_deposit: bool = False
    deposit_cents: int = Field(default=0, ge=0)
    teacher_id: uuid.UUID | None = None
    is_published: bool = False


class EventUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    location: str | None = None
    capacity: int | None = Field(default=None, ge=1)
    price_cents: int | None = Field(default=None, ge=0)
    requires_deposit: bool | None = None
    deposit_cents: int | None = Field(default=None, ge=0)
    is_published: bool | None = None


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    type: EventType
    starts_at: datetime
    ends_at: datetime
    location: str | None
    capacity: int
    price_cents: int
    requires_deposit: bool
    deposit_cents: int
    teacher_id: uuid.UUID | None
    is_published: bool


class EventRegister(BaseModel):
    member_id: uuid.UUID


class PaymentConfirm(BaseModel):
    amount_cents: int = Field(ge=0)


class EventRegistrationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_id: uuid.UUID
    member_id: uuid.UUID
    status: EventRegistrationStatus
    amount_paid_cents: int
