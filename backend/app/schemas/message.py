import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.user import UserRole


class ContactRead(BaseModel):
    """A user the current user can start or continue a conversation with."""

    id: uuid.UUID
    full_name: str | None
    email: str
    role: UserRole


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_id: uuid.UUID
    body: str
    read_at: datetime | None
    created_at: datetime


class ConversationRead(BaseModel):
    """A conversation summary for the inbox list."""

    id: uuid.UUID
    other_user_id: uuid.UUID
    other_user_name: str | None
    other_user_role: UserRole
    last_message: str | None
    last_message_at: datetime | None
    unread_count: int


class StartConversationRequest(BaseModel):
    recipient_id: uuid.UUID


class SendMessageRequest(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class UnreadCount(BaseModel):
    unread: int
