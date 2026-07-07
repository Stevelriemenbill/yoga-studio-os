import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_staff
from app.db.session import get_db
from app.schemas.member import MemberCreate, MemberRead, MemberUpdate
from app.services import member as member_service
from app.services.member import MemberRepository

router = APIRouter(prefix="/members", tags=["members"])


@router.get("", response_model=list[MemberRead])
async def list_members(
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    return await MemberRepository(db, current.tenant_id).list(limit=500)


@router.post("", response_model=MemberRead, status_code=status.HTTP_201_CREATED)
async def create_member(
    data: MemberCreate,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    return await member_service.create_member(db, current.tenant_id, data)


@router.get("/{member_id}", response_model=MemberRead)
async def get_member(
    member_id: uuid.UUID,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    member = await MemberRepository(db, current.tenant_id).get(member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return member


@router.patch("/{member_id}", response_model=MemberRead)
async def update_member(
    member_id: uuid.UUID,
    data: MemberUpdate,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    member = await MemberRepository(db, current.tenant_id).get(member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return await member_service.update_member(db, member, data)


@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_member(
    member_id: uuid.UUID,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    repo = MemberRepository(db, current.tenant_id)
    member = await repo.get(member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    await repo.delete(member)
    await db.commit()
