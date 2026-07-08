import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import GUID
from app.models.mixins import TenantMixin

if TYPE_CHECKING:
    from app.models.session import CourseSession


class CourseLevel(str, enum.Enum):
    ALL = "all"
    BEGINNER = "beginner"
    INTERMEDIATE = "advanced_beginner"
    ADVANCED = "advanced"


class Room(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = "rooms"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Course(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """A course template. Concrete occurrences are CourseSession rows."""

    __tablename__ = "courses"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    level: Mapped[CourseLevel] = mapped_column(
        Enum(CourseLevel, native_enum=False, length=32),
        default=CourseLevel.ALL,
        nullable=False,
    )

    room_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("rooms.id", ondelete="SET NULL"), nullable=True
    )
    teacher_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    max_participants: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    min_participants: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)

    #: Default location for this course. A concrete session may override it.
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    #: Whether the course is held online by default.
    is_online: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    #: Meeting link for online courses (e.g. Zoom URL).
    online_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    #: Free-form registration / preparation info shown to members
    #: (e.g. how to register, what to bring, access details).
    registration_info: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    #: Whether attendance of this course's sessions counts toward
    #: teacher-training hours (studio-configurable metadata).
    counts_for_training: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    room: Mapped["Room | None"] = relationship(lazy="selectin")
    sessions: Mapped[list["CourseSession"]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    attachments: Mapped[list["CourseAttachment"]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class CourseAttachment(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """A file attached to a course (e.g. registration info PDF)."""

    __tablename__ = "course_attachments"

    course_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    #: Original filename as uploaded.
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    #: Stored filename on disk (relative to the media directory).
    stored_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    course: Mapped["Course"] = relationship(back_populates="attachments")
