import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import (
    AcceptInviteRequest,
    AcceptInviteResult,
    InvitedMember,
    LoginRequest,
    RefreshRequest,
    RegistrationResult,
    StudioRegistration,
    TenantRead,
    Token,
    UserRead,
)
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=RegistrationResult,
    status_code=status.HTTP_201_CREATED,
)
async def register_studio(
    data: StudioRegistration, db: AsyncSession = Depends(get_db)
) -> RegistrationResult:
    """Register a new studio (tenant) with its first admin user."""
    try:
        tenant, user = await auth_service.register_studio(db, data)
    except auth_service.AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc

    token = auth_service.issue_tokens(user)
    return RegistrationResult(
        tenant=TenantRead.model_validate(tenant),
        user=UserRead.model_validate(user),
        token=token,
    )


@router.post("/login", response_model=Token)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)) -> Token:
    try:
        user = await auth_service.authenticate(
            db, data.tenant_slug, data.email, data.password
        )
    except auth_service.AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc

    return auth_service.issue_tokens(user)


@router.post("/refresh", response_model=Token)
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)) -> Token:
    try:
        payload = decode_token(data.refresh_token, expected_type="refresh")
        user_id = payload.get("sub")
        tenant_id = payload.get("tid")
        if user_id is None or tenant_id is None:
            raise JWTError("Missing claims")
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        ) from exc

    result = await db.execute(
        select(User).where(
            User.id == uuid.UUID(user_id),
            User.tenant_id == uuid.UUID(tenant_id),
        )
    )
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    subject = str(user.id)
    tid = str(user.tenant_id)
    return Token(
        access_token=create_access_token(subject, tid, user.role.value),
        refresh_token=create_refresh_token(subject, tid, user.role.value),
    )


@router.get("/me", response_model=UserRead)
async def me(current: CurrentUser = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(current.user)


@router.get("/invite/{token}", response_model=InvitedMember)
async def preview_invite(
    token: str, db: AsyncSession = Depends(get_db)
) -> InvitedMember:
    """Public: validate an invitation and return details to prefill the form."""
    try:
        member = await auth_service.get_invited_member(db, token)
    except auth_service.AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    tenant = await db.get(Tenant, member.tenant_id)
    return InvitedMember(
        first_name=member.first_name,
        last_name=member.last_name,
        email=member.email or "",
        studio_name=tenant.name if tenant else "",
    )


@router.post(
    "/invite/accept",
    response_model=AcceptInviteResult,
    status_code=status.HTTP_201_CREATED,
)
async def accept_invite(
    data: AcceptInviteRequest, db: AsyncSession = Depends(get_db)
) -> AcceptInviteResult:
    """Public: consume an invite, create the member's login and auto-login."""
    try:
        user = await auth_service.accept_invite(db, data.token, data.password)
    except auth_service.AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    return AcceptInviteResult(
        user=UserRead.model_validate(user),
        token=auth_service.issue_tokens(user),
    )
