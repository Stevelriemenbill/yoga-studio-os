import enum

from sqlalchemy import JSON, Enum, Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.mixins import TenantMixin

# Portable JSON column (JSONB on Postgres, JSON elsewhere).
JSONType = JSON().with_variant(JSONB(), "postgresql")


class InsightType(str, enum.Enum):
    FORECAST = "forecast"
    RECOMMENDATION = "recommendation"
    ANOMALY = "anomaly"
    ASSISTANT_ANSWER = "assistant_answer"


class AIInsight(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = "ai_insights"

    type: Mapped[InsightType] = mapped_column(
        Enum(InsightType, native_enum=False, length=32), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    # Confidence 0..1 for forecasts.
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Arbitrary structured payload (e.g. forecasted numbers, referenced entities).
    data: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
