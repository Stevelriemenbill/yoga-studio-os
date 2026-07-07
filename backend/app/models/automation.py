import enum

from sqlalchemy import Boolean, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.mixins import TenantMixin
from app.models.notification import NotificationChannel


class AutomationTrigger(str, enum.Enum):
    INACTIVE_DAYS = "inactive_days"  # member not seen for N days
    AFTER_BOOKING = "after_booking"
    BEFORE_SESSION = "before_session"  # smart reminder
    AFTER_NO_SHOW = "after_no_show"
    MEMBERSHIP_EXPIRING = "membership_expiring"


class AutomationRule(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """Configurable retention / lifecycle automation.

    Example: trigger=INACTIVE_DAYS, threshold_days=30 -> send a discount.
    """

    __tablename__ = "automation_rules"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    trigger: Mapped[AutomationTrigger] = mapped_column(
        Enum(AutomationTrigger, native_enum=False, length=32), nullable=False
    )
    # Days threshold (meaning depends on trigger, e.g. inactivity days or lead time).
    threshold_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, native_enum=False, length=20),
        default=NotificationChannel.EMAIL,
        nullable=False,
    )
    message_template: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
