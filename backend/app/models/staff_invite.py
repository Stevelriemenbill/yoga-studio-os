import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import GUID
from app.models.mixins import TenantMixin
from app.models.user import UserRole


class StaffInviteStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REVOKED = "revoked"


class StaffInvite(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """A pending invitation for someone to join a studio as a staff user.

    Unlike member invitations (which reference an existing ``Member`` contact
    record), a staff invitation is standalone: it carries the target email,
    display name and role, and creates a fresh ``User`` when accepted.

    At most one PENDING invite per (tenant, email) is enforced by the service.
    """

    __tablename__ = "staff_invites"

    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False, length=32), nullable=False
    )
    status: Mapped[StaffInviteStatus] = mapped_column(
        Enum(StaffInviteStatus, native_enum=False, length=20),
        default=StaffInviteStatus.PENDING,
        nullable=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    #: User created when the invitation was accepted (for reference).
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    #: The staff user who sent the invitation.
    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    def __repr__(self) -> str:
        return f"<StaffInvite {self.email} ({self.role.value}, {self.status.value})>"
