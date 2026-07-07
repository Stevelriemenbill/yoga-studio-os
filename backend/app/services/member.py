import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import TenantRepository
from app.models.member import Member
from app.schemas.member import MemberCreate, MemberUpdate


class MemberRepository(TenantRepository[Member]):
    model = Member


async def create_member(
    db: AsyncSession, tenant_id: uuid.UUID, data: MemberCreate
) -> Member:
    repo = MemberRepository(db, tenant_id)
    member = repo.add(Member(**data.model_dump()))
    await db.commit()
    await db.refresh(member)
    return member


async def update_member(
    db: AsyncSession, member: Member, data: MemberUpdate
) -> Member:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(member, field, value)
    await db.commit()
    await db.refresh(member)
    return member
