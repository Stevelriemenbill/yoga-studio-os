import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import GUID
from app.models.mixins import TenantMixin


class JoinRequestStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"


class JoinRequest(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """A prospective member's request to join a studio.

    Submitted publicly (no auth) via the studio's join page. The studio reviews
    pending requests and either approves (creating a Member + invitation) or
    declines. This keeps the studio in control while removing the need for an
    in-person first contact.
    """

    __tablename__ = "join_requests"

    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    last_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[JoinRequestStatus] = mapped_column(
        Enum(JoinRequestStatus, native_enum=False, length=20),
        default=JoinRequestStatus.PENDING,
        nullable=False,
    )
    #: Member created when the request was approved (for reference).
    member_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("members.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<JoinRequest {self.email} ({self.status.value})>"
