from pydantic import BaseModel, EmailStr, Field


class SendMessageIn(BaseModel):
    lead_id: int
    subject: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1)
    to: EmailStr | None = None  # defaults to lead.email when omitted


class SendMessageOut(BaseModel):
    contact_id: int
    external_id: str


class SyncResult(BaseModel):
    fetched: int
    matched: int
    skipped_duplicates: int
    skipped_unmatched: int
