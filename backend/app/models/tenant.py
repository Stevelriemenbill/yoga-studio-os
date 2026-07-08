from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Tenant(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A studio. Root of the multi-tenant hierarchy."""

    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # White-label branding (future extension: customizable studio appearance).
    brand_primary_color: Mapped[str | None] = mapped_column(String(9), nullable=True)
    brand_logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    custom_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Studio-wide appearance, chosen by the studio admin and applied for every
    # user of the studio (staff and members alike).
    #: Accent colour preset name (e.g. "emerald", "blue", "violet", ...).
    theme_preset: Mapped[str] = mapped_column(
        String(32), nullable=False, default="emerald", server_default="emerald"
    )
    #: Colour mode: "light" or "dark".
    theme_mode: Mapped[str] = mapped_column(
        String(16), nullable=False, default="light", server_default="light"
    )

    # Check-in time window (minutes) relative to a session's start, configurable
    # per studio by the studio admin.
    #: How many minutes before start check-in opens.
    checkin_opens_before: Mapped[int] = mapped_column(
        Integer, nullable=False, default=30, server_default="30"
    )
    #: How many minutes after start check-in stays open.
    checkin_closes_after: Mapped[int] = mapped_column(
        Integer, nullable=False, default=15, server_default="15"
    )
    #: Minutes after start beyond which a check-in counts as "late".
    checkin_late_threshold: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5, server_default="5"
    )

    def __repr__(self) -> str:
        return f"<Tenant {self.slug}>"
