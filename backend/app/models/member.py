import enum
import uuid
from datetime import date

from sqlalchemy import Date, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import GUID
from app.models.mixins import TenantMixin


class MembershipType(str, enum.Enum):
    DROP_IN = "drop_in"
    PUNCH_CARD = "punch_card"  # 10er-Karte
    UNLIMITED = "unlimited"
    NONE = "none"


class Member(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = "members"

    # Optional link to a user account (a member may just be a contact record).
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    last_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    membership_type: Mapped[MembershipType] = mapped_column(
        Enum(MembershipType, native_enum=False, length=20),
        default=MembershipType.NONE,
        nullable=False,
    )
    membership_valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Remaining credits for punch cards.
    credits: Mapped[int] = mapped_column(default=0, nullable=False)

    # Reliability score 0..1 used by the intelligent waitlist / overbooking.
    reliability_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    # Average response time to waitlist offers, in seconds.
    avg_response_seconds: Mapped[int | None] = mapped_column(nullable=True)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
