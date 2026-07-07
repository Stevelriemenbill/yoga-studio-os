import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_staff
from app.db.session import get_db
from app.models.tenant import Tenant
from app.schemas.integrations import (
    ApiKeyCreate,
    ApiKeyCreated,
    ApiKeyRead,
    BrandingRead,
    BrandingUpdate,
    WebhookCreate,
    WebhookRead,
)
from app.services import integrations as integrations_service
from app.services.integrations import (
    ApiKeyRepository,
    WebhookEndpointRepository,
)

router = APIRouter(prefix="/integrations", tags=["integrations"])


# --- API keys ---
@router.get("/api-keys", response_model=list[ApiKeyRead])
async def list_api_keys(
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    return await ApiKeyRepository(db, current.tenant_id).list()


@router.post("/api-keys", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    data: ApiKeyCreate,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    key, raw = await integrations_service.create_api_key(
        db, current.tenant_id, data.name
    )
    return ApiKeyCreated(
        id=key.id, name=key.name, prefix=key.prefix, is_active=key.is_active, key=raw
    )


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: uuid.UUID,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    repo = ApiKeyRepository(db, current.tenant_id)
    key = await repo.get(key_id)
    if key is None:
        raise HTTPException(status_code=404, detail="API key not found")
    key.is_active = False
    await db.commit()


# --- Webhooks ---
@router.get("/webhooks", response_model=list[WebhookRead])
async def list_webhooks(
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    return await WebhookEndpointRepository(db, current.tenant_id).list()


@router.post("/webhooks", response_model=WebhookRead, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    data: WebhookCreate,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    return await integrations_service.create_webhook(
        db, current.tenant_id, data.url, data.event_types
    )


@router.delete("/webhooks/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: uuid.UUID,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    repo = WebhookEndpointRepository(db, current.tenant_id)
    endpoint = await repo.get(webhook_id)
    if endpoint is None:
        raise HTTPException(status_code=404, detail="Webhook not found")
    await repo.delete(endpoint)
    await db.commit()


# --- White-label branding ---
async def _get_tenant(db: AsyncSession, tenant_id: uuid.UUID) -> Tenant:
    tenant = (
        await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    ).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.get("/branding", response_model=BrandingRead)
async def get_branding(
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    return await _get_tenant(db, current.tenant_id)


@router.patch("/branding", response_model=BrandingRead)
async def update_branding(
    data: BrandingUpdate,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    tenant = await _get_tenant(db, current.tenant_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(tenant, field, value)
    await db.commit()
    await db.refresh(tenant)
    return tenant
