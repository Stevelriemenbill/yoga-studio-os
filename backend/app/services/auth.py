import uuid
from datetime import UTC, datetime, timedelta

from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_invite_token,
    create_refresh_token,
    create_staff_invite_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.member import Member
from app.models.notification import NotificationChannel, NotificationStatus
from app.models.staff_invite import StaffInvite, StaffInviteStatus
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.schemas.auth import STAFF_INVITE_ROLES, StudioRegistration, Token
from app.services import notification as notification_service
from app.services.channels import get_sender


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
) -> tuple[str, str, bool]:
    """Create an invitation for a member to claim a login account.

    Returns ``(token, invite_url, email_delivered)``. The invitation
    notification is delivered immediately (not left for the background worker),
    so callers know right away whether an email actually went out.

    ``email_delivered`` is ``True`` only if a real email provider is configured
    and accepted the message. In development (no SMTP configured) it is
    ``False`` and the caller should surface the ``invite_url`` directly instead
    of implying an email was sent.
    """
    if member.email is None:
        raise AuthError("Member has no email address to invite")
    if member.user_id is not None:
        raise AuthError("Member already has a linked account")

    token = create_invite_token(str(member.id), str(tenant_id))
    invite_url = f"{settings.FRONTEND_URL.rstrip('/')}/invite/{token}"

    notification = await notification_service.enqueue(
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
        recipient_email=member.email,
    )

    # Deliver right away instead of waiting for the ARQ worker, so the UI can
    # report the true outcome.
    delivered = await notification_service.deliver(db, notification)
    email_delivered = (
        delivered.status == NotificationStatus.SENT
        and get_sender(NotificationChannel.EMAIL).delivers_real_email
    )
    return token, invite_url, email_delivered


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


# --- Staff invitations -----------------------------------------------------


async def invite_staff(
    db: AsyncSession,
    tenant_id,
    *,
    email: str,
    role: UserRole,
    full_name: str | None = None,
    invited_by: uuid.UUID | None = None,
) -> tuple[StaffInvite, str, bool]:
    """Create a staff invitation and send it. Returns (invite, url, delivered)."""
    if role not in STAFF_INVITE_ROLES:
        raise AuthError("This role cannot be invited as staff")

    email = email.lower()

    # Reject if a user with this email already exists in the tenant.
    existing_user = await get_user_by_email(db, tenant_id, email)
    if existing_user is not None:
        raise AuthError("A user with this email already exists")

    # Reject if there is already an open invitation for this email.
    open_invite = (
        await db.execute(
            select(StaffInvite).where(
                StaffInvite.tenant_id == tenant_id,
                StaffInvite.email == email,
                StaffInvite.status == StaffInviteStatus.PENDING,
            )
        )
    ).scalar_one_or_none()
    if open_invite is not None:
        raise AuthError("An open invitation for this email already exists")

    invite = StaffInvite(
        tenant_id=tenant_id,
        email=email,
        full_name=full_name,
        role=role,
        status=StaffInviteStatus.PENDING,
        expires_at=datetime.now(UTC)
        + timedelta(days=settings.INVITE_TOKEN_EXPIRE_DAYS),
        invited_by=invited_by,
    )
    db.add(invite)
    await db.flush()  # assigns invite.id

    token = create_staff_invite_token(str(invite.id), str(tenant_id), role.value)
    invite_url = f"{settings.FRONTEND_URL.rstrip('/')}/staff-invite/{token}"

    tenant = await db.get(Tenant, tenant_id)
    studio_name = tenant.name if tenant else "dein Studio"
    notification = await notification_service.enqueue(
        db,
        tenant_id,
        channel=NotificationChannel.EMAIL,
        subject=f"Einladung ins Team von {studio_name}",
        body=(
            f"Hallo{(' ' + full_name) if full_name else ''},\n\n"
            f"{studio_name} lädt dich als {role.value} ins Team ein. "
            "Aktiviere dein Konto und setze dein Passwort über folgenden Link:\n\n"
            f"{invite_url}\n\n"
            f"Der Link ist {settings.INVITE_TOKEN_EXPIRE_DAYS} Tage gültig."
        ),
        template="staff_invite",
        recipient_email=email,
    )
    delivered = await notification_service.deliver(db, notification)
    await db.commit()
    await db.refresh(invite)

    email_delivered = (
        delivered.status == NotificationStatus.SENT
        and get_sender(NotificationChannel.EMAIL).delivers_real_email
    )
    return invite, invite_url, email_delivered


async def list_staff(db: AsyncSession, tenant_id) -> tuple[list[User], list[StaffInvite]]:
    """Return staff users and pending invitations for the tenant."""
    from app.models.user import STAFF_ROLES

    users = list(
        (
            await db.execute(
                select(User).where(
                    User.tenant_id == tenant_id,
                    User.role.in_(list(STAFF_ROLES)),
                )
            )
        )
        .scalars()
        .all()
    )
    invites = list(
        (
            await db.execute(
                select(StaffInvite).where(
                    StaffInvite.tenant_id == tenant_id,
                    StaffInvite.status == StaffInviteStatus.PENDING,
                )
            )
        )
        .scalars()
        .all()
    )
    return users, invites


async def revoke_staff_invite(db: AsyncSession, tenant_id, invite_id: uuid.UUID) -> None:
    invite = (
        await db.execute(
            select(StaffInvite).where(
                StaffInvite.id == invite_id,
                StaffInvite.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if invite is None:
        raise AuthError("Invitation not found")
    if invite.status != StaffInviteStatus.PENDING:
        raise AuthError("Invitation is no longer pending")
    invite.status = StaffInviteStatus.REVOKED
    await db.commit()


async def get_staff_invite(db: AsyncSession, token: str) -> StaffInvite:
    """Validate a staff invite token and return the pending invitation."""
    try:
        payload = decode_token(token, expected_type="staff_invite")
        invite_id = uuid.UUID(payload["sub"])
        tenant_id = uuid.UUID(payload["tid"])
    except (JWTError, KeyError, ValueError) as exc:
        raise AuthError("Invalid or expired invitation") from exc

    invite = (
        await db.execute(
            select(StaffInvite).where(
                StaffInvite.id == invite_id,
                StaffInvite.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if invite is None:
        raise AuthError("Invalid or expired invitation")
    if invite.status != StaffInviteStatus.PENDING:
        raise AuthError("This invitation is no longer valid")
    return invite


async def accept_staff_invite(db: AsyncSession, token: str, password: str) -> User:
    """Consume a staff invite: create the staff user and mark invite accepted."""
    invite = await get_staff_invite(db, token)

    existing = await get_user_by_email(db, invite.tenant_id, invite.email)
    if existing is not None:
        raise AuthError("An account with this email already exists")

    user = User(
        tenant_id=invite.tenant_id,
        email=invite.email.lower(),
        hashed_password=hash_password(password),
        full_name=invite.full_name,
        role=invite.role,
        is_active=True,
    )
    db.add(user)
    await db.flush()  # assigns user.id

    invite.status = StaffInviteStatus.ACCEPTED
    invite.accepted_at = datetime.now(UTC)
    invite.user_id = user.id
    await db.commit()
    await db.refresh(user)
    return user
