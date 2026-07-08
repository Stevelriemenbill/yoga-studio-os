import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import TenantRepository
from app.models.join_request import JoinRequest, JoinRequestStatus
from app.models.member import Member


class JoinRequestError(Exception):
    """Raised for join-request business errors."""


class JoinRequestRepository(TenantRepository[JoinRequest]):
    model = JoinRequest

    async def by_status(
        self, status: JoinRequestStatus | None = None
    ) -> list[JoinRequest]:
        query = self._base_query().order_by(JoinRequest.created_at.desc())
        if status is not None:
            query = query.where(JoinRequest.status == status)
        result = await self.db.execute(query)
        return list(result.scalars().all())


async def submit_join_request(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    first_name: str,
    last_name: str,
    email: str,
    phone: str | None = None,
    message: str | None = None,
) -> JoinRequest:
    """Public: record a prospective member's request to join a studio."""
    email = email.lower()

    # Avoid duplicate open requests from the same email.
    existing = (
        await db.execute(
            select(JoinRequest).where(
                JoinRequest.tenant_id == tenant_id,
                JoinRequest.email == email,
                JoinRequest.status == JoinRequestStatus.PENDING,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        # Idempotent: return the existing pending request instead of erroring,
        # so a double submit doesn't leak information or create clutter.
        return existing

    req = JoinRequest(
        tenant_id=tenant_id,
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone,
        message=message,
        status=JoinRequestStatus.PENDING,
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return req


async def approve_join_request(
    db: AsyncSession, tenant_id: uuid.UUID, request_id: uuid.UUID
) -> tuple[JoinRequest, Member, str, bool]:
    """Approve a request: create a Member and send an invitation.

    Returns ``(request, member, invite_url, email_delivered)``.
    """
    # Imported here to avoid a circular import (auth imports models/services).
    from app.services import auth as auth_service

    req = await JoinRequestRepository(db, tenant_id).get(request_id)
    if req is None:
        raise JoinRequestError("Join request not found")
    if req.status != JoinRequestStatus.PENDING:
        raise JoinRequestError("Join request is no longer pending")

    member = Member(
        tenant_id=tenant_id,
        first_name=req.first_name,
        last_name=req.last_name,
        email=req.email,
        phone=req.phone,
    )
    db.add(member)
    await db.flush()  # assigns member.id

    req.status = JoinRequestStatus.APPROVED
    req.member_id = member.id
    req.reviewed_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(member)
    await db.refresh(req)

    # Send the member invitation so they can set a password and log in.
    _token, invite_url, email_delivered = await auth_service.invite_member(
        db, tenant_id, member
    )
    return req, member, invite_url, email_delivered


async def decline_join_request(
    db: AsyncSession, tenant_id: uuid.UUID, request_id: uuid.UUID
) -> JoinRequest:
    req = await JoinRequestRepository(db, tenant_id).get(request_id)
    if req is None:
        raise JoinRequestError("Join request not found")
    if req.status != JoinRequestStatus.PENDING:
        raise JoinRequestError("Join request is no longer pending")
    req.status = JoinRequestStatus.DECLINED
    req.reviewed_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(req)
    return req
