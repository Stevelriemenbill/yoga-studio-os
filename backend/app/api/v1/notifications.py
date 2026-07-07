
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_staff
from app.db.session import get_db
from app.models.session import CourseSession
from app.schemas.notification import (
    NotificationCreate,
    NotificationRead,
    ProcessResult,
    SessionReminderRequest,
)
from app.services import notification as notification_service
from app.services.notification import NotificationRepository

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("", response_model=NotificationRead, status_code=status.HTTP_201_CREATED)
async def create_notification(
    data: NotificationCreate,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    return await notification_service.enqueue(
        db,
        current.tenant_id,
        channel=data.channel,
        body=data.body,
        member_id=data.member_id,
        subject=data.subject,
        scheduled_for=data.scheduled_for,
        template=data.template,
    )


@router.get("", response_model=list[NotificationRead])
async def list_notifications(
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    return await NotificationRepository(db, current.tenant_id).list(limit=200)


@router.post("/reminders", response_model=list[NotificationRead], status_code=201)
async def schedule_reminders(
    data: SessionReminderRequest,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    session = (
        await db.execute(
            select(CourseSession).where(
                CourseSession.tenant_id == current.tenant_id,
                CourseSession.id == data.session_id,
            )
        )
    ).scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return await notification_service.schedule_session_reminders(
        db,
        current.tenant_id,
        session,
        channel=data.channel,
        reminder_at=data.reminder_at,
    )


@router.post("/process", response_model=ProcessResult)
async def process_pending(
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Deliver all due pending notifications (invoked by worker / cron)."""
    sent = await notification_service.process_pending(db, current.tenant_id)
    return ProcessResult(sent=sent)
