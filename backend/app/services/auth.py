import uuid

from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_invite_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.member import Member
from app.models.notification import NotificationChannel
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.schemas.auth import StudioRegistration, Token
from app.services import notification as notification_service


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


async def invite_member(
    db: AsyncSession, tenant_id, member: Member
) -> tuple[str, str]:
    """Create an invitation for a member to claim a login account.

    Returns (token, invite_url). Sends an email notification if the member
    has an address on file.
    """
    if member.email is None:
        raise AuthError("Member has no email address to invite")
    if member.user_id is not None:
        raise AuthError("Member already has a linked account")

    token = create_invite_token(str(member.id), str(tenant_id))
    invite_url = f"{settings.FRONTEND_URL.rstrip('/')}/invite/{token}"

    await notification_service.enqueue(
        db,
        tenant_id,
        channel=NotificationChannel.EMAIL,
        member_id=member.id,
        subject="Willkommen – aktiviere dein Konto",
        body=(
            f"Hallo {member.first_name},\n\n"
            "dein Studio hat ein Konto für dich angelegt. "
            "Aktiviere es und setze dein Passwort über folgenden Link:\n\n"
            f"{invite_url}\n\n"
            f"Der Link ist {settings.INVITE_TOKEN_EXPIRE_DAYS} Tage gültig."
        ),
        template="member_invite",
    )
    return token, invite_url


async def get_invited_member(db: AsyncSession, token: str) -> Member:
    """Validate an invite token and return the target member."""
    try:
        payload = decode_token(token, expected_type="invite")
        member_id = uuid.UUID(payload["sub"])
        tenant_id = uuid.UUID(payload["tid"])
    except (JWTError, KeyError, ValueError) as exc:
        raise AuthError("Invalid or expired invitation") from exc

    result = await db.execute(
        select(Member).where(
            Member.id == member_id, Member.tenant_id == tenant_id
        )
    )
    member = result.scalar_one_or_none()
    if member is None:
        raise AuthError("Invalid or expired invitation")
    if member.user_id is not None:
        raise AuthError("This invitation has already been used")
    return member


async def accept_invite(db: AsyncSession, token: str, password: str) -> User:
    """Consume an invite token: create a MEMBER user and link it to the member."""
    member = await get_invited_member(db, token)
    if member.email is None:
        raise AuthError("Member has no email address")

    existing = await get_user_by_email(db, member.tenant_id, member.email)
    if existing is not None:
        raise AuthError("An account with this email already exists")

    user = User(
        tenant_id=member.tenant_id,
        email=member.email.lower(),
        hashed_password=hash_password(password),
        full_name=member.full_name,
        role=UserRole.MEMBER,
        is_active=True,
    )
    db.add(user)
    await db.flush()  # assigns user.id

    member.user_id = user.id
    await db.commit()
    await db.refresh(user)
    return user
