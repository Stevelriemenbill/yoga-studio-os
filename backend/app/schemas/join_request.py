import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class JoinRequestCreate(BaseModel):
    """Public payload submitted by a prospective member."""

    first_name: str = Field(min_length=1, max_length=120)
    last_name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=50)
    message: str | None = Field(default=None, max_length=2000)


class JoinRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    first_name: str
    last_name: str
    email: EmailStr
    phone: str | None
    message: str | None
    status: str
    created_at: datetime
    reviewed_at: datetime | None = None


class PublicStudio(BaseModel):
    """Minimal public studio info shown on the join page."""

    name: str
    slug: str
