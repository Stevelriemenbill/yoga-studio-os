from sqlalchemy import Boolean, String
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

    def __repr__(self) -> str:
        return f"<Tenant {self.slug}>"
