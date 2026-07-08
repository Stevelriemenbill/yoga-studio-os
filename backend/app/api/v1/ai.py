import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_staff
from app.db.session import get_db
from app.schemas.ai import (
    AssistantQuery,
    InsightRead,
    StudentNoteCreate,
    StudentNoteRead,
)
from app.services import ai as ai_service
from app.services import student_note as note_service
from app.services.ai import InsightRepository

router = APIRouter(prefix="/care", tags=["care"])


@router.get("/insights", response_model=list[InsightRead])
async def list_insights(
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    return await InsightRepository(db, current.tenant_id).list()


@router.post("/insights/generate", response_model=list[InsightRead])
async def generate_insights(
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Fürsorgliche Hinweise erzeugen: wer war lange nicht da, wer feiert bald?"""
    return await ai_service.care_insights(db, current.tenant_id)


@router.get("/students-needing-care")
async def students_needing_care(
    quiet_days: int = 21,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Schüler:innen, die aus ihrem Rhythmus gefallen sind – zum persönlichen Melden."""
    return await ai_service.students_needing_care(
        db, current.tenant_id, quiet_days=quiet_days
    )


@router.get("/journey/{member_id}")
async def student_journey(
    member_id: uuid.UUID,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Die Praxis-Reise einer Person: Konstanz, Stile, Meilensteine."""
    journey = await ai_service.student_journey(db, current.tenant_id, member_id)
    if not journey:
        raise HTTPException(status_code=404, detail="Member not found")
    return journey


@router.post("/assistant", response_model=InsightRead)
async def assistant(
    query: AssistantQuery,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    return await ai_service.assistant_answer(db, current.tenant_id, query.question)


# --- Lehrer-Notizen zu Schüler:innen ---


@router.get("/notes/{member_id}", response_model=list[StudentNoteRead])
async def list_notes(
    member_id: uuid.UUID,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    return await note_service.StudentNoteRepository(
        db, current.tenant_id
    ).for_member(member_id)


@router.post("/notes/{member_id}", response_model=StudentNoteRead)
async def add_note(
    member_id: uuid.UUID,
    data: StudentNoteCreate,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    return await note_service.add_note(
        db, current.tenant_id, member_id, data.body, current.user.id
    )


@router.delete("/notes/{note_id}", status_code=204)
async def delete_note(
    note_id: uuid.UUID,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    note = await note_service.get_note(db, current.tenant_id, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    await note_service.StudentNoteRepository(db, current.tenant_id).delete(note)
    await db.commit()
