import uuid

from pydantic import BaseModel, ConfigDict, Field


# --- API keys ---
class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class ApiKeyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    prefix: str
    is_active: bool


class ApiKeyCreated(ApiKeyRead):
    # Plaintext key, returned only once at creation time.
    key: str


# --- Webhooks ---
class WebhookCreate(BaseModel):
    url: str = Field(min_length=1, max_length=500)
    event_types: list[str] = Field(default_factory=list)


class WebhookRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    url: str
    event_types: list[str]
    is_active: bool


# --- White-label branding ---
class BrandingUpdate(BaseModel):
    brand_primary_color: str | None = Field(default=None, max_length=9)
    brand_logo_url: str | None = Field(default=None, max_length=500)
    custom_domain: str | None = Field(default=None, max_length=255)


class BrandingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    brand_primary_color: str | None
    brand_logo_url: str | None
    custom_domain: str | None
