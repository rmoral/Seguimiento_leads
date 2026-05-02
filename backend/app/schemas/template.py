from datetime import datetime

from pydantic import BaseModel, Field


class TemplateBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    subject: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1)
    variables: str | None = Field(default=None, max_length=500)


class TemplateCreate(TemplateBase):
    pass


class TemplateUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    subject: str | None = Field(default=None, max_length=300)
    body: str | None = None
    variables: str | None = Field(default=None, max_length=500)


class TemplateOut(TemplateBase):
    id: int
    tenant_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
