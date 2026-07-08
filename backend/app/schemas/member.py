import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.member import MembershipType


class MemberCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=120)
    last_name: str = Field(min_length=1, max_length=120)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    notes: str | None = None
    membership_type: MembershipType = MembershipType.NONE
    membership_valid_until: date | None = None
    credits: int = Field(default=0, ge=0)
    user_id: uuid.UUID | None = None


class MemberUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=120)
    last_name: str | None = Field(default=None, min_length=1, max_length=120)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    notes: str | None = None
    membership_type: MembershipType | None = None
    membership_valid_until: date | None = None
    credits: int | None = Field(default=None, ge=0)


class MemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    first_name: str
    last_name: str
    email: str | None
    phone: str | None
    notes: str | None
    membership_type: MembershipType
    membership_valid_until: date | None
    credits: int
    reliability_score: float
    user_id: uuid.UUID | None
