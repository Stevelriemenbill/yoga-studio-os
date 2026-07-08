import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import TenantRepository
from app.models.member import Member
from app.schemas.member import MemberCreate, MemberUpdate


class MemberRepository(TenantRepository[Member]):
    model = Member

    async def by_user_id(self, user_id: uuid.UUID) -> Member | None:
        """Return the member record linked to a login user, if any."""
        result = await self.db.execute(
            self._base_query().where(Member.user_id == user_id)
        )
        return result.scalar_one_or_none()


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
