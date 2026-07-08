import uuid
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import decode_token
from app.db.session import get_db
from app.models.member import Member
from app.models.user import STAFF_ROLES, User, UserRole

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login", auto_error=False
)


@dataclass
class CurrentUser:
    """Authenticated principal with resolved tenant scope."""

    user: User
    tenant_id: uuid.UUID
    role: UserRole


_CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    if not token:
        raise _CREDENTIALS_EXC

    try:
        payload = decode_token(token, expected_type="access")
        user_id = payload.get("sub")
        tenant_id = payload.get("tid")
        if user_id is None or tenant_id is None:
            raise _CREDENTIALS_EXC
    except JWTError as exc:
        raise _CREDENTIALS_EXC from exc

    result = await db.execute(
        select(User).where(
            User.id == uuid.UUID(user_id),
            User.tenant_id == uuid.UUID(tenant_id),
        )
    )
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise _CREDENTIALS_EXC

    return CurrentUser(user=user, tenant_id=user.tenant_id, role=user.role)


def require_roles(*roles: UserRole) -> Callable:
    """Dependency factory enforcing that the current user has one of the roles."""

    async def _checker(
        current: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if current.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current

    return _checker


async def require_staff(
    current: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    if current.role not in STAFF_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff access required",
        )
    return current


async def require_admin(
    current: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Only the studio admin may pass (e.g. studio-wide settings)."""
    if current.role is not UserRole.STUDIO_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Studio admin access required",
        )
    return current


async def get_current_member(
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Member:
    """Resolve the Member record linked to the authenticated user.

    Used by member self-service endpoints so that actions are always scoped to
    the caller's own member record — the member id is never taken from client
    input. Raises 404 if the login is not linked to a member (e.g. staff-only
    accounts).
    """
    # Import here to avoid a circular import (services import models/deps).
    from app.services.member import MemberRepository

    member = await MemberRepository(db, current.tenant_id).by_user_id(
        current.user.id
    )
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No member profile linked to this account",
        )
    return member
