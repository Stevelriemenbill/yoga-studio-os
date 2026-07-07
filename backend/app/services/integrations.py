"""Public API keys + outbound webhooks (integrations / marketplace foundation).

* API keys let third parties authenticate against the public API. Only the
  hash is stored; the plaintext is returned once at creation.
* Webhook endpoints receive signed HTTP callbacks for subscribed event types.
  Deliveries are recorded for auditing/retry.

The webhook dispatch integrates with :mod:`app.core.events`: whenever a domain
event is published, :func:`dispatch_event` fans it out to matching endpoints.
"""

import hashlib
import hmac
import json
import secrets
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import TenantRepository
from app.models.integrations import (
    ApiKey,
    WebhookDelivery,
    WebhookDeliveryStatus,
    WebhookEndpoint,
)

# --- API keys --------------------------------------------------------------


class ApiKeyRepository(TenantRepository[ApiKey]):
    model = ApiKey


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


async def create_api_key(
    db: AsyncSession, tenant_id: uuid.UUID, name: str
) -> tuple[ApiKey, str]:
    """Create a key. Returns (record, plaintext) — plaintext shown only once."""
    raw = f"sk_{secrets.token_urlsafe(32)}"
    prefix = raw[:8]
    repo = ApiKeyRepository(db, tenant_id)
    key = repo.add(
        ApiKey(name=name, prefix=prefix, key_hash=_hash_key(raw), is_active=True)
    )
    await db.commit()
    await db.refresh(key)
    return key, raw


async def verify_api_key(db: AsyncSession, raw: str) -> ApiKey | None:
    """Resolve a plaintext key to its (active) record across all tenants."""
    key_hash = _hash_key(raw)
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.key_hash == key_hash, ApiKey.is_active.is_(True)
        )
    )
    return result.scalar_one_or_none()


# --- Webhooks --------------------------------------------------------------


class WebhookEndpointRepository(TenantRepository[WebhookEndpoint]):
    model = WebhookEndpoint

    async def active_for_event(self, event_type: str) -> list[WebhookEndpoint]:
        result = await self.db.execute(
            self._base_query().where(WebhookEndpoint.is_active.is_(True))
        )
        endpoints = list(result.scalars().all())
        return [e for e in endpoints if event_type in (e.event_types or [])]


async def create_webhook(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    url: str,
    event_types: list[str],
) -> WebhookEndpoint:
    repo = WebhookEndpointRepository(db, tenant_id)
    endpoint = repo.add(
        WebhookEndpoint(
            url=url,
            secret=secrets.token_urlsafe(24),
            event_types=event_types,
            is_active=True,
        )
    )
    await db.commit()
    await db.refresh(endpoint)
    return endpoint


def sign_payload(secret: str, body: bytes) -> str:
    """HMAC-SHA256 signature receivers use to verify authenticity."""
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


async def dispatch_event(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    event_type: str,
    payload: dict,
    *,
    client: httpx.AsyncClient | None = None,
) -> list[WebhookDelivery]:
    """Deliver an event to every subscribed active endpoint for the tenant."""
    repo = WebhookEndpointRepository(db, tenant_id)
    endpoints = await repo.active_for_event(event_type)
    deliveries: list[WebhookDelivery] = []
    if not endpoints:
        return deliveries

    body = json.dumps({"type": event_type, "data": payload}).encode()
    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(timeout=5.0)

    try:
        for endpoint in endpoints:
            delivery = WebhookDelivery(
                tenant_id=tenant_id,
                endpoint_id=str(endpoint.id),
                event_type=event_type,
                payload=payload,
                attempts=1,
            )
            try:
                resp = await client.post(
                    endpoint.url,
                    content=body,
                    headers={
                        "Content-Type": "application/json",
                        "X-StudioOS-Signature": sign_payload(endpoint.secret, body),
                        "X-StudioOS-Event": event_type,
                    },
                )
                delivery.response_code = resp.status_code
                delivery.status = (
                    WebhookDeliveryStatus.DELIVERED
                    if resp.is_success
                    else WebhookDeliveryStatus.FAILED
                )
            except httpx.HTTPError:
                delivery.status = WebhookDeliveryStatus.FAILED
            db.add(delivery)
            deliveries.append(delivery)
        await db.commit()
    finally:
        if owns_client:
            await client.aclose()

    return deliveries
