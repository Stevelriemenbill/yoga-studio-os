import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.insight import InsightType


class InsightRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: InsightType
    title: str
    body: str
    confidence: float | None
    data: dict | None
    created_at: datetime


class AssistantQuery(BaseModel):
    question: str


class StudentNoteCreate(BaseModel):
    body: str


class StudentNoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    member_id: uuid.UUID
    author_id: uuid.UUID | None
    body: str
    created_at: datetime
