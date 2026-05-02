from datetime import datetime

from pydantic import BaseModel, EmailStr


class EmailAccountOut(BaseModel):
    id: int
    provider: str
    email: EmailStr
    last_synced_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class AuthorizationUrlOut(BaseModel):
    authorization_url: str
