import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user
from app.db.session import get_db
from app.schemas.message import (
    ContactRead,
    ConversationRead,
    MessageRead,
    SendMessageRequest,
    StartConversationRequest,
    UnreadCount,
)
from app.services import messaging as messaging_service

router = APIRouter(prefix="/messages", tags=["messages"])


@router.get("/contacts", response_model=list[ContactRead])
async def list_contacts(
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ContactRead]:
    """Users in the same studio the caller can message."""
    users = await messaging_service.list_contacts(
        db, current.tenant_id, current.user.id
    )
    return [
        ContactRead(id=u.id, full_name=u.full_name, email=u.email, role=u.role)
        for u in users
    ]


@router.get("/conversations", response_model=list[ConversationRead])
async def list_conversations(
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ConversationRead]:
    rows = await messaging_service.list_conversations(
        db, current.tenant_id, current.user.id
    )
    return [
        ConversationRead(
            id=conv.id,
            other_user_id=conv.other_user_id(current.user.id),
            other_user_name=(other.full_name if other else None),
            other_user_role=(other.role if other else "member"),
            last_message=(last.body if last else None),
            last_message_at=conv.last_message_at,
            unread_count=unread,
        )
        for conv, other, last, unread in rows
    ]


@router.get("/unread", response_model=UnreadCount)
async def unread_count(
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UnreadCount:
    total = await messaging_service.total_unread(
        db, current.tenant_id, current.user.id
    )
    return UnreadCount(unread=total)


@router.post(
    "/conversations",
    response_model=ConversationRead,
    status_code=status.HTTP_201_CREATED,
)
async def start_conversation(
    data: StartConversationRequest,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConversationRead:
    """Open (or reuse) a 1:1 conversation with another user."""
    try:
        conv = await messaging_service.get_or_create_conversation(
            db, current.tenant_id, current.user.id, data.recipient_id
        )
    except messaging_service.MessagingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    other_id = conv.other_user_id(current.user.id)
    contacts = await messaging_service.list_contacts(
        db, current.tenant_id, current.user.id
    )
    other = next((u for u in contacts if u.id == other_id), None)
    return ConversationRead(
        id=conv.id,
        other_user_id=other_id,
        other_user_name=(other.full_name if other else None),
        other_user_role=(other.role if other else "member"),
        last_message=None,
        last_message_at=conv.last_message_at,
        unread_count=0,
    )


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageRead],
)
async def list_messages(
    conversation_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MessageRead]:
    try:
        messages = await messaging_service.list_messages(
            db, current.tenant_id, current.user.id, conversation_id
        )
    except messaging_service.MessagingError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [MessageRead.model_validate(m) for m in messages]


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageRead,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    conversation_id: uuid.UUID,
    data: SendMessageRequest,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageRead:
    try:
        message = await messaging_service.send_message(
            db, current.tenant_id, current.user.id, conversation_id, data.body
        )
    except messaging_service.MessagingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return MessageRead.model_validate(message)


@router.post(
    "/conversations/{conversation_id}/read", response_model=UnreadCount
)
async def mark_read(
    conversation_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UnreadCount:
    try:
        await messaging_service.mark_read(
            db, current.tenant_id, current.user.id, conversation_id
        )
    except messaging_service.MessagingError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    total = await messaging_service.total_unread(
        db, current.tenant_id, current.user.id
    )
    return UnreadCount(unread=total)
