import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.checkin import AttendanceStatus, CheckInMethod


class QRCheckInRequest(BaseModel):
    """Scan a member's QR token at a session."""

    token: str
    session_id: uuid.UUID
    device_id: str | None = None


class ManualCheckInRequest(BaseModel):
    member_id: uuid.UUID
    session_id: uuid.UUID
    device_id: str | None = None


class CheckInRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    member_id: uuid.UUID
    session_id: uuid.UUID | None
    booking_id: uuid.UUID | None
    checked_in_at: datetime
    method: CheckInMethod
    device_id: str | None


class MemberPassRead(BaseModel):
    member_id: uuid.UUID
    token: str
    qr_payload: str


class AttendanceSet(BaseModel):
    member_id: uuid.UUID
    status: AttendanceStatus


class AttendanceConfirm(BaseModel):
    """Staff confirms or rejects a pending self check-in."""

    member_id: uuid.UUID


class AttendanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    member_id: uuid.UUID
    status: AttendanceStatus
    recorded_by: uuid.UUID | None
