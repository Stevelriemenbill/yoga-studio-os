import enum

from sqlalchemy import JSON, Boolean, Enum, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.mixins import TenantMixin

JSONType = JSON().with_variant(JSONB(), "postgresql")


class ApiKey(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """Per-tenant API key for the public integrations API.

    Only a hash of the key is stored; the plaintext is shown once on creation.
    """

    __tablename__ = "api_keys"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    # Short non-secret prefix to help identify a key in listings (e.g. "sk_ab12").
    prefix: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    key_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class WebhookEndpoint(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """A tenant-configured HTTP endpoint that receives domain event callbacks."""

    __tablename__ = "webhook_endpoints"

    url: Mapped[str] = mapped_column(String(500), nullable=False)
    # Secret used to sign payloads (HMAC-SHA256) so receivers can verify origin.
    secret: Mapped[str] = mapped_column(String(128), nullable=False)
    # Event types this endpoint subscribes to, e.g. ["booking.created", ...].
    event_types: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class WebhookDeliveryStatus(str, enum.Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"


class WebhookDelivery(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """An attempt to deliver an event to a webhook endpoint (audit trail)."""

    __tablename__ = "webhook_deliveries"

    endpoint_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONType, nullable=False)
    status: Mapped[WebhookDeliveryStatus] = mapped_column(
        Enum(WebhookDeliveryStatus, native_enum=False, length=20),
        default=WebhookDeliveryStatus.PENDING,
        nullable=False,
    )
    response_code: Mapped[int | None] = mapped_column(nullable=True)
    attempts: Mapped[int] = mapped_column(default=0, nullable=False)
