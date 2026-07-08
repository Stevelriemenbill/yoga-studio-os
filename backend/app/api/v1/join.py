import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_staff
from app.db.session import get_db
from app.schemas.auth import InviteResult
from app.schemas.join_request import (
    JoinRequestCreate,
    JoinRequestRead,
    PublicStudio,
)
from app.services import auth as auth_service
from app.services import join_request as join_service

# Public router (no auth) for the studio join page.
public_router = APIRouter(prefix="/join", tags=["join"])

# Staff router for reviewing requests.
router = APIRouter(prefix="/join-requests", tags=["join"])


@public_router.get("/{slug}", response_model=PublicStudio)
async def public_studio(slug: str, db: AsyncSession = Depends(get_db)) -> PublicStudio:
    """Public: resolve a studio by slug so the join page can show its name."""
    tenant = await auth_service.get_tenant_by_slug(db, slug)
    if tenant is None or not tenant.is_active:
        raise HTTPException(status_code=404, detail="Studio not found")
    return PublicStudio(name=tenant.name, slug=tenant.slug)


@public_router.post(
    "/{slug}", response_model=JoinRequestRead, status_code=status.HTTP_201_CREATED
)
async def submit_join_request(
    slug: str,
    data: JoinRequestCreate,
    db: AsyncSession = Depends(get_db),
) -> JoinRequestRead:
    """Public: a prospective member requests to join a studio."""
    tenant = await auth_service.get_tenant_by_slug(db, slug)
    if tenant is None or not tenant.is_active:
        raise HTTPException(status_code=404, detail="Studio not found")
    req = await join_service.submit_join_request(
        db,
        tenant.id,
        first_name=data.first_name,
        last_name=data.last_name,
        email=data.email,
        phone=data.phone,
        message=data.message,
    )
    return JoinRequestRead.model_validate(req)


@router.get("", response_model=list[JoinRequestRead])
async def list_join_requests(
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> list[JoinRequestRead]:
    """Staff: list join requests (most recent first)."""
    requests = await join_service.JoinRequestRepository(
        db, current.tenant_id
    ).by_status()
    return [JoinRequestRead.model_validate(r) for r in requests]


@router.post("/{request_id}/approve", response_model=InviteResult)
async def approve_join_request(
    request_id: uuid.UUID,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> InviteResult:
    """Staff: approve a request -> create member + send invitation."""
    try:
        _req, _member, url, email_delivered = await join_service.approve_join_request(
            db, current.tenant_id, request_id
        )
    except join_service.JoinRequestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return InviteResult(invite_url=url, token="", email_delivered=email_delivered)


@router.post("/{request_id}/decline", response_model=JoinRequestRead)
async def decline_join_request(
    request_id: uuid.UUID,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> JoinRequestRead:
    """Staff: decline a request."""
    try:
        req = await join_service.decline_join_request(
            db, current.tenant_id, request_id
        )
    except join_service.JoinRequestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return JoinRequestRead.model_validate(req)
