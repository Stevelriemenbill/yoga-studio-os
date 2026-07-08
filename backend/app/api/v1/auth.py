import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_admin
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
    InvitedStaff,
    LoginRequest,
    MeRead,
    RefreshRequest,
    RegistrationResult,
    StudioRegistration,
    TenantRead,
    ThemeRead,
    ThemeUpdate,
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


@router.get("/me", response_model=MeRead)
async def me(
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MeRead:
    tenant = await db.get(Tenant, current.tenant_id)
    return MeRead(
        id=current.user.id,
        tenant_id=current.user.tenant_id,
        email=current.user.email,
        full_name=current.user.full_name,
        role=current.user.role,
        is_active=current.user.is_active,
        studio_name=tenant.name if tenant else "",
        theme_preset=tenant.theme_preset if tenant else "emerald",
        theme_mode=tenant.theme_mode if tenant else "light",
    )


@router.get("/theme", response_model=ThemeRead)
async def get_theme(
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ThemeRead:
    """The studio-wide theme. Readable by any authenticated user so the app
    shell can apply it for members and staff alike."""
    tenant = await db.get(Tenant, current.tenant_id)
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Studio not found"
        )
    return ThemeRead.model_validate(tenant)


@router.patch("/theme", response_model=ThemeRead)
async def update_theme(
    data: ThemeUpdate,
    current: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ThemeRead:
    """Set the studio-wide theme. Studio admin only."""
    tenant = await db.get(Tenant, current.tenant_id)
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Studio not found"
        )
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(tenant, field, value)
    await db.commit()
    await db.refresh(tenant)
    return ThemeRead.model_validate(tenant)


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


@router.get("/staff-invite/{token}", response_model=InvitedStaff)
async def preview_staff_invite(
    token: str, db: AsyncSession = Depends(get_db)
) -> InvitedStaff:
    """Public: validate a staff invitation and return details to prefill the form."""
    try:
        invite = await auth_service.get_staff_invite(db, token)
    except auth_service.AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    tenant = await db.get(Tenant, invite.tenant_id)
    return InvitedStaff(
        email=invite.email,
        full_name=invite.full_name,
        role=invite.role,
        studio_name=tenant.name if tenant else "",
    )


@router.post(
    "/staff-invite/accept",
    response_model=AcceptInviteResult,
    status_code=status.HTTP_201_CREATED,
)
async def accept_staff_invite(
    data: AcceptInviteRequest, db: AsyncSession = Depends(get_db)
) -> AcceptInviteResult:
    """Public: consume a staff invite, create the staff login and auto-login."""
    try:
        user = await auth_service.accept_staff_invite(db, data.token, data.password)
    except auth_service.AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    return AcceptInviteResult(
        user=UserRead.model_validate(user),
        token=auth_service.issue_tokens(user),
    )
