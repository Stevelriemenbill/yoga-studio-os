from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.schemas.auth import StudioRegistration, Token


class AuthError(Exception):
    """Raised for authentication/registration business errors."""


async def get_tenant_by_slug(db: AsyncSession, slug: str) -> Tenant | None:
    result = await db.execute(select(Tenant).where(Tenant.slug == slug))
    return result.scalar_one_or_none()


async def get_user_by_email(
    db: AsyncSession, tenant_id, email: str
) -> User | None:
    result = await db.execute(
        select(User).where(User.tenant_id == tenant_id, User.email == email.lower())
    )
    return result.scalar_one_or_none()


def issue_tokens(user: User) -> Token:
    subject = str(user.id)
    tenant_id = str(user.tenant_id)
    return Token(
        access_token=create_access_token(subject, tenant_id, user.role.value),
        refresh_token=create_refresh_token(subject, tenant_id, user.role.value),
    )


async def register_studio(
    db: AsyncSession, data: StudioRegistration
) -> tuple[Tenant, User]:
    existing = await get_tenant_by_slug(db, data.studio_slug)
    if existing is not None:
        raise AuthError("A studio with this slug already exists")

    tenant = Tenant(name=data.studio_name, slug=data.studio_slug, is_active=True)
    db.add(tenant)
    await db.flush()  # assigns tenant.id

    admin = User(
        tenant_id=tenant.id,
        email=data.admin_email.lower(),
        hashed_password=hash_password(data.admin_password),
        full_name=data.admin_full_name,
        role=UserRole.STUDIO_ADMIN,
        is_active=True,
    )
    db.add(admin)
    await db.commit()
    await db.refresh(tenant)
    await db.refresh(admin)
    return tenant, admin


async def authenticate(
    db: AsyncSession, tenant_slug: str, email: str, password: str
) -> User:
    tenant = await get_tenant_by_slug(db, tenant_slug)
    if tenant is None or not tenant.is_active:
        raise AuthError("Invalid credentials")

    user = await get_user_by_email(db, tenant.id, email)
    if user is None or not user.is_active:
        raise AuthError("Invalid credentials")

    if not verify_password(password, user.hashed_password):
        raise AuthError("Invalid credentials")

    return user
