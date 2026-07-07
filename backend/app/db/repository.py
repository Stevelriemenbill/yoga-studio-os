import uuid
from typing import Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class TenantRepository(Generic[ModelT]):
    """Base repository that always scopes queries by tenant_id.

    All tenant-scoped data access should go through a subclass to guarantee
    that no cross-tenant leakage occurs.
    """

    model: type[ModelT]

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID) -> None:
        self.db = db
        self.tenant_id = tenant_id

    def _base_query(self):
        return select(self.model).where(self.model.tenant_id == self.tenant_id)

    async def get(self, obj_id: uuid.UUID) -> ModelT | None:
        result = await self.db.execute(
            self._base_query().where(self.model.id == obj_id)
        )
        return result.scalar_one_or_none()

    async def list(self, *, limit: int = 100, offset: int = 0) -> list[ModelT]:
        result = await self.db.execute(
            self._base_query().limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def count(self) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(self.model).where(
                self.model.tenant_id == self.tenant_id
            )
        )
        return int(result.scalar_one())

    def add(self, obj: ModelT) -> ModelT:
        # Enforce tenant scoping on write.
        obj.tenant_id = self.tenant_id
        self.db.add(obj)
        return obj

    async def delete(self, obj: ModelT) -> None:
        await self.db.delete(obj)
