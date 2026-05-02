from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class LeadBase(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    email: EmailStr | None = None
    company: str | None = Field(default=None, max_length=180)
    phone: str | None = Field(default=None, max_length=60)
    source: str | None = Field(default=None, max_length=80)
    status: str = Field(default="new", max_length=40)
    notes: str | None = None


class LeadCreate(LeadBase):
    pass


class LeadUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=180)
    email: EmailStr | None = None
    company: str | None = Field(default=None, max_length=180)
    phone: str | None = Field(default=None, max_length=60)
    source: str | None = Field(default=None, max_length=80)
    status: str | None = Field(default=None, max_length=40)
    notes: str | None = None


class LeadOut(LeadBase):
    id: int
    tenant_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
