from pydantic import BaseModel, Field


class TenantSettingsOut(BaseModel):
    id: int
    name: str
    plan: str
    reminder_after_days: int
    auto_reminders_enabled: bool

    class Config:
        from_attributes = True


class TenantSettingsUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    reminder_after_days: int | None = Field(default=None, ge=1, le=365)
    auto_reminders_enabled: bool | None = None
