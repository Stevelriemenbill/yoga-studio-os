import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ParticipationEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: uuid.UUID
    course_name: str
    starts_at: datetime
    hours: float
    counts_for_training: bool


class ParticipationHistory(BaseModel):
    total_sessions: int
    total_hours: float
    training_hours: float
    entries: list[ParticipationEntry]
