from datetime import datetime

from pydantic import BaseModel, Field


class FollowUpBase(BaseModel):
    lead_id: int
    template_id: int | None = None
    scheduled_at: datetime
    status: str = Field(default="pending", max_length=20)
    notes: str | None = None


class FollowUpCreate(FollowUpBase):
    pass


class FollowUpUpdate(BaseModel):
    template_id: int | None = None
    scheduled_at: datetime | None = None
    status: str | None = Field(default=None, max_length=20)
    notes: str | None = None


class FollowUpOut(FollowUpBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
