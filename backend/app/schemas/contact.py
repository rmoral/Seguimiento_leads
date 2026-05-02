from datetime import datetime

from pydantic import BaseModel, Field


class ContactBase(BaseModel):
    lead_id: int
    type: str = Field(default="email", max_length=20)
    direction: str = Field(default="out", max_length=10)
    subject: str | None = Field(default=None, max_length=300)
    body: str | None = None
    sent_at: datetime | None = None


class ContactCreate(ContactBase):
    pass


class ContactOut(ContactBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
