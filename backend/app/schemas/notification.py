import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.notification import (
    NotificationChannel,
    NotificationStatus,
)


class NotificationCreate(BaseModel):
    channel: NotificationChannel
    body: str
    member_id: uuid.UUID | None = None
    subject: str | None = None
    scheduled_for: datetime | None = None
    template: str | None = None


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    member_id: uuid.UUID | None
    channel: NotificationChannel
    subject: str | None
    body: str
    status: NotificationStatus
    scheduled_for: datetime | None
    sent_at: datetime | None
    template: str | None


class SessionReminderRequest(BaseModel):
    session_id: uuid.UUID
    channel: NotificationChannel = NotificationChannel.PUSH
    reminder_at: datetime | None = None


class ProcessResult(BaseModel):
    sent: int
