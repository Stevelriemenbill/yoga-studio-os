import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import TenantRepository
from app.models.student_note import StudentNote


class StudentNoteRepository(TenantRepository[StudentNote]):
    model = StudentNote

    async def for_member(self, member_id: uuid.UUID) -> list[StudentNote]:
        result = await self.db.execute(
            self._base_query()
            .where(StudentNote.member_id == member_id)
            .order_by(StudentNote.created_at.desc())
        )
        return list(result.scalars().all())


async def add_note(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    member_id: uuid.UUID,
    body: str,
    author_id: uuid.UUID | None,
) -> StudentNote:
    repo = StudentNoteRepository(db, tenant_id)
    note = repo.add(
        StudentNote(member_id=member_id, body=body, author_id=author_id)
    )
    await db.commit()
    await db.refresh(note)
    return note


async def get_note(
    db: AsyncSession, tenant_id: uuid.UUID, note_id: uuid.UUID
) -> StudentNote | None:
    result = await db.execute(
        select(StudentNote).where(
            StudentNote.tenant_id == tenant_id, StudentNote.id == note_id
        )
    )
    return result.scalar_one_or_none()
