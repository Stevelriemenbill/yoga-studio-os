import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_admin
from app.db.session import get_db
from app.schemas.auth import (
    StaffInviteCreate,
    StaffInviteRead,
    StaffInviteResult,
    StaffListEntry,
)
from app.services import auth as auth_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[StaffListEntry])
async def list_staff(
    current: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[StaffListEntry]:
    """List staff accounts and pending invitations. Studio admin only."""
    users, invites = await auth_service.list_staff(db, current.tenant_id)
    entries: list[StaffListEntry] = [
        StaffListEntry(
            kind="user",
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            role=u.role,
            is_active=u.is_active,
            status="active" if u.is_active else "inactive",
        )
        for u in users
    ]
    entries += [
        StaffListEntry(
            kind="invite",
            id=inv.id,
            email=inv.email,
            full_name=inv.full_name,
            role=inv.role,
            is_active=False,
            status="pending",
        )
        for inv in invites
    ]
    return entries


@router.post(
    "/invite",
    response_model=StaffInviteResult,
    status_code=status.HTTP_201_CREATED,
)
async def invite_staff(
    data: StaffInviteCreate,
    current: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> StaffInviteResult:
    """Invite someone to join the studio team (teacher/manager/reception)."""
    try:
        invite, url, email_delivered = await auth_service.invite_staff(
            db,
            current.tenant_id,
            email=data.email,
            role=data.role,
            full_name=data.full_name,
            invited_by=current.user.id,
        )
    except auth_service.AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return StaffInviteResult(
        invite=StaffInviteRead.model_validate(invite),
        invite_url=url,
        email_delivered=email_delivered,
    )


@router.delete("/invite/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invite(
    invite_id: uuid.UUID,
    current: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    try:
        await auth_service.revoke_staff_invite(db, current.tenant_id, invite_id)
    except auth_service.AuthError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
