import enum
import uuid
from datetime import date

from sqlalchemy import (
    Date,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

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


class TrainingProgram(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """A teacher-training curriculum template (e.g. the 2-year training).

    Concrete runs are TrainingCohort rows; required hours per area live in
    TrainingRequirement rows linked via ``program_id``.
    """

    __tablename__ = "training_programs"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    #: Nominal length of the program in months (e.g. 24 for a 2-year training).
    duration_months: Mapped[int] = mapped_column(
        Integer, default=24, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    requirements: Mapped[list["TrainingRequirement"]] = relationship(
        back_populates="program",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    cohorts: Mapped[list["TrainingCohort"]] = relationship(
        back_populates="program",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class CohortStatus(str, enum.Enum):
    PLANNED = "planned"
    RUNNING = "running"
    COMPLETED = "completed"


class TrainingCohort(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """A concrete run (Jahrgang) of a training program.

    Several cohorts of the same program run in parallel (e.g. two starts per
    year over a two-year program => four active cohorts).
    """

    __tablename__ = "training_cohorts"

    program_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("training_programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[CohortStatus] = mapped_column(
        Enum(CohortStatus, native_enum=False, length=20),
        default=CohortStatus.PLANNED,
        nullable=False,
    )

    program: Mapped["TrainingProgram"] = relationship(back_populates="cohorts")
    enrollments: Mapped[list["TrainingEnrollment"]] = relationship(
        back_populates="cohort",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class EnrollmentStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    WITHDRAWN = "withdrawn"


class TrainingEnrollment(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """Links a trainee (member) to a cohort."""

    __tablename__ = "training_enrollments"
    __table_args__ = (
        UniqueConstraint(
            "cohort_id", "member_id", name="uq_enrollment_cohort_member"
        ),
    )

    cohort_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("training_cohorts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    enrolled_on: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[EnrollmentStatus] = mapped_column(
        Enum(EnrollmentStatus, native_enum=False, length=20),
        default=EnrollmentStatus.ACTIVE,
        nullable=False,
    )

    cohort: Mapped["TrainingCohort"] = relationship(back_populates="enrollments")


class TrainingRequirement(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """Required hours per area for a training program."""

    __tablename__ = "training_requirements"

    #: Program this requirement belongs to. Nullable for legacy studio-wide
    #: requirements created before programs existed.
    program_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("training_programs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    area: Mapped[TrainingArea] = mapped_column(
        Enum(TrainingArea, native_enum=False, length=20), nullable=False
    )
    required_hours: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    program: Mapped["TrainingProgram | None"] = relationship(
        back_populates="requirements"
    )


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
