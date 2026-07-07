import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.automation import AutomationTrigger
from app.models.notification import NotificationChannel


class AutomationRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    trigger: AutomationTrigger
    threshold_days: int = Field(default=0, ge=0)
    channel: NotificationChannel = NotificationChannel.EMAIL
    message_template: str
    is_active: bool = True


class AutomationRuleUpdate(BaseModel):
    name: str | None = None
    threshold_days: int | None = Field(default=None, ge=0)
    channel: NotificationChannel | None = None
    message_template: str | None = None
    is_active: bool | None = None


class AutomationRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    trigger: AutomationTrigger
    threshold_days: int
    channel: NotificationChannel
    message_template: str
    is_active: bool


class AutomationRunResult(BaseModel):
    total_enqueued: int
    per_rule: dict[str, int]
