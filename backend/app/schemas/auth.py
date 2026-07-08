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


class MeRead(UserRead):
    """The authenticated user plus the studio context needed by the app shell.

    Carries the studio name (for display) and the studio-wide theme so the
    frontend can apply the same look for every user of the studio.
    """

    studio_name: str
    theme_preset: str
    theme_mode: str


class TenantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    is_active: bool


#: Accent colour presets the studio admin can choose from. Mirrors the
#: frontend theme module; validated here to reject arbitrary values.
THEME_PRESETS = frozenset(
    {"emerald", "blue", "violet", "amber", "rose", "teal", "indigo"}
)
THEME_MODES = frozenset({"light", "dark"})


class ThemeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    theme_preset: str
    theme_mode: str


class ThemeUpdate(BaseModel):
    theme_preset: str | None = Field(default=None, max_length=32)
    theme_mode: str | None = Field(default=None, max_length=16)

    @field_validator("theme_preset")
    @classmethod
    def _validate_preset(cls, v: str | None) -> str | None:
        if v is not None and v not in THEME_PRESETS:
            raise ValueError(f"unknown theme preset: {v}")
        return v

    @field_validator("theme_mode")
    @classmethod
    def _validate_mode(cls, v: str | None) -> str | None:
        if v is not None and v not in THEME_MODES:
            raise ValueError(f"unknown theme mode: {v}")
        return v


class RegistrationResult(BaseModel):
    tenant: TenantRead
    user: UserRead
    token: Token


class InviteResult(BaseModel):
    """Returned to staff after creating an invitation."""

    invite_url: str
    token: str
    #: ``True`` only if a real email was actually delivered. In development
    #: (no SMTP configured) this is ``False`` and the UI should share the
    #: ``invite_url`` manually instead of implying an email was sent.
    email_delivered: bool = False


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
