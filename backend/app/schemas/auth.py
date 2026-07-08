import re
import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.user import UserRole

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_slug: str


class StudioRegistration(BaseModel):
    """Creates a new tenant (studio) together with its first admin user."""

    studio_name: str = Field(min_length=2, max_length=255)
    studio_slug: str = Field(min_length=2, max_length=120)
    admin_email: EmailStr
    admin_password: str = Field(min_length=8, max_length=128)
    admin_full_name: str | None = Field(default=None, max_length=255)

    @field_validator("studio_slug")
    @classmethod
    def _validate_slug(cls, v: str) -> str:
        v = v.lower().strip()
        if not SLUG_RE.match(v):
            raise ValueError(
                "slug must be lowercase alphanumeric with single hyphens"
            )
        return v


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    email: EmailStr
    full_name: str | None
    role: UserRole
    is_active: bool


class TenantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    is_active: bool


class RegistrationResult(BaseModel):
    tenant: TenantRead
    user: UserRead
    token: Token


class InviteResult(BaseModel):
    """Returned to staff after creating an invitation."""

    invite_url: str
    token: str


class InvitedMember(BaseModel):
    """Public preview of an invitation, used to prefill the accept form."""

    first_name: str
    last_name: str
    email: EmailStr
    studio_name: str


class AcceptInviteRequest(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=128)


class AcceptInviteResult(BaseModel):
    user: UserRead
    token: Token
