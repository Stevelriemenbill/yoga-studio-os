import enum
import uuid
from datetime import date

from sqlalchemy import Date, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import GUID
from app.models.mixins import TenantMixin


class TrainingArea(str, enum.Enum):
    PRACTICE = "practice"  # Praktische Stunden
    OBSERVATION = "observation"  # Hospitation
    MEDITATION = "meditation"
    THEORY = "theory"
    TEACHING = "teaching"
    OTHER = "other"


class TrainingRequirement(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """Required hours per area for a training program."""

    __tablename__ = "training_requirements"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    area: Mapped[TrainingArea] = mapped_column(
        Enum(TrainingArea, native_enum=False, length=20), nullable=False
    )
    required_hours: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)


class TrainingHours(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """A logged training-hour entry for a trainee (Yogalehrer in Ausbildung)."""

    __tablename__ = "training_hours"

    trainee_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("members.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("course_sessions.id", ondelete="SET NULL"), nullable=True
    )
    teacher_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    area: Mapped[TrainingArea] = mapped_column(
        Enum(TrainingArea, native_enum=False, length=20), nullable=False
    )
    hours: Mapped[float] = mapped_column(Float, nullable=False)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
