"""Signed state tokens used to bind an OAuth callback to the right user."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from app.core.config import settings

_ALG = "HS256"
_ISSUER = "seguimiento-leads/oauth"


def make_state(user_id: int, tenant_id: int, provider: str, ttl_minutes: int = 10) -> str:
    payload = {
        "iss": _ISSUER,
        "sub": str(user_id),
        "tid": tenant_id,
        "prv": provider,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=_ALG)


def parse_state(token: str) -> dict[str, Any]:
    try:
        data = jwt.decode(token, settings.JWT_SECRET, algorithms=[_ALG])
    except JWTError as exc:
        raise ValueError("Invalid OAuth state") from exc
    if data.get("iss") != _ISSUER:
        raise ValueError("Invalid OAuth state issuer")
    return {
        "user_id": int(data["sub"]),
        "tenant_id": int(data["tid"]),
        "provider": data["prv"],
    }
