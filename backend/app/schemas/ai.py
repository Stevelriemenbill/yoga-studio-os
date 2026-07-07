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
