import uuid

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import GUID
from app.models.mixins import TenantMixin


class StudentNote(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """Eine private, unterstützende Notiz einer Lehrkraft zu einer Schülerin
    oder einem Schüler.

    Gedacht für persönliche Begleitung – Verletzungen, Ziele, Vorlieben,
    besondere Umstände – damit der Unterricht menschlicher und individueller
    werden kann. Bewusst schlicht gehalten.
    """

    __tablename__ = "student_notes"

    member_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Verfassende Lehrkraft.
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
