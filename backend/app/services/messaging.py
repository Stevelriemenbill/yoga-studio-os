import uuid
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Conversation, Message
from app.models.user import User


class MessagingError(Exception):
    """Raised for messaging business errors."""


def _canonical_pair(a: uuid.UUID, b: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID]:
    """Order a user pair deterministically so each pair maps to one conversation."""
    return (a, b) if str(a) < str(b) else (b, a)


async def list_contacts(
    db: AsyncSession, tenant_id: uuid.UUID, current_user_id: uuid.UUID
) -> list[User]:
    """All other active users in the tenant the caller may message."""
    result = await db.execute(
        select(User).where(
            User.tenant_id == tenant_id,
            User.id != current_user_id,
            User.is_active.is_(True),
        )
    )
    return list(result.scalars().all())


async def get_or_create_conversation(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    recipient_id: uuid.UUID,
) -> Conversation:
    if recipient_id == user_id:
        raise MessagingError("Cannot start a conversation with yourself")

    recipient = (
        await db.execute(
            select(User).where(
                User.id == recipient_id,
                User.tenant_id == tenant_id,
                User.is_active.is_(True),
            )
        )
    ).scalar_one_or_none()
    if recipient is None:
        raise MessagingError("Recipient not found")

    low, high = _canonical_pair(user_id, recipient_id)
    conversation = (
        await db.execute(
            select(Conversation).where(
                Conversation.tenant_id == tenant_id,
                Conversation.user_low_id == low,
                Conversation.user_high_id == high,
            )
        )
    ).scalar_one_or_none()
    if conversation is None:
        conversation = Conversation(
            tenant_id=tenant_id, user_low_id=low, user_high_id=high
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
    return conversation


async def _get_conversation_for_user(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    conversation_id: uuid.UUID,
) -> Conversation:
    conversation = (
        await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if conversation is None:
        raise MessagingError("Conversation not found")
    if user_id not in (conversation.user_low_id, conversation.user_high_id):
        raise MessagingError("Not a participant of this conversation")
    return conversation


async def send_message(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    conversation_id: uuid.UUID,
    body: str,
) -> Message:
    conversation = await _get_conversation_for_user(
        db, tenant_id, user_id, conversation_id
    )
    message = Message(
        tenant_id=tenant_id,
        conversation_id=conversation.id,
        sender_id=user_id,
        body=body,
    )
    db.add(message)
    conversation.last_message_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(message)
    return message


async def list_messages(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    conversation_id: uuid.UUID,
) -> list[Message]:
    await _get_conversation_for_user(db, tenant_id, user_id, conversation_id)
    result = await db.execute(
        select(Message)
        .where(
            Message.tenant_id == tenant_id,
            Message.conversation_id == conversation_id,
        )
        .order_by(Message.created_at)
    )
    return list(result.scalars().all())


async def mark_read(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    conversation_id: uuid.UUID,
) -> int:
    """Mark all messages the caller received in this conversation as read."""
    await _get_conversation_for_user(db, tenant_id, user_id, conversation_id)
    now = datetime.now(UTC)
    result = await db.execute(
        select(Message).where(
            Message.tenant_id == tenant_id,
            Message.conversation_id == conversation_id,
            Message.sender_id != user_id,
            Message.read_at.is_(None),
        )
    )
    messages = list(result.scalars().all())
    for m in messages:
        m.read_at = now
    await db.commit()
    return len(messages)


async def list_conversations(
    db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID
) -> list[tuple[Conversation, User | None, Message | None, int]]:
    """Return (conversation, other_user, last_message, unread_count) tuples."""
    convs = list(
        (
            await db.execute(
                select(Conversation)
                .where(
                    Conversation.tenant_id == tenant_id,
                    or_(
                        Conversation.user_low_id == user_id,
                        Conversation.user_high_id == user_id,
                    ),
                )
                .order_by(Conversation.last_message_at.desc().nullslast())
            )
        )
        .scalars()
        .all()
    )

    out: list[tuple[Conversation, User | None, Message | None, int]] = []
    for conv in convs:
        other_id = conv.other_user_id(user_id)
        other = (
            await db.execute(select(User).where(User.id == other_id))
        ).scalar_one_or_none()

        last = (
            await db.execute(
                select(Message)
                .where(Message.conversation_id == conv.id)
                .order_by(Message.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        unread = (
            await db.execute(
                select(func.count(Message.id)).where(
                    Message.conversation_id == conv.id,
                    Message.sender_id != user_id,
                    Message.read_at.is_(None),
                )
            )
        ).scalar_one()

        out.append((conv, other, last, int(unread or 0)))
    return out


async def total_unread(
    db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID
) -> int:
    """Count all unread messages addressed to the caller across conversations."""
    result = await db.execute(
        select(func.count(Message.id))
        .select_from(Message)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(
            Message.tenant_id == tenant_id,
            Message.sender_id != user_id,
            Message.read_at.is_(None),
            or_(
                Conversation.user_low_id == user_id,
                Conversation.user_high_id == user_id,
            ),
        )
    )
    return int(result.scalar_one() or 0)
