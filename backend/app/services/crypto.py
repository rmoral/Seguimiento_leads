"""Symmetric encryption for OAuth tokens stored at rest."""
from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _derive_key() -> bytes:
    """Use ENCRYPTION_KEY when set, otherwise derive a dev key from JWT_SECRET.

    The derived key is deterministic so dev runs survive restarts; production
    deployments MUST set ENCRYPTION_KEY explicitly.
    """
    if settings.ENCRYPTION_KEY:
        return settings.ENCRYPTION_KEY.encode()
    digest = hashlib.sha256(settings.JWT_SECRET.encode()).digest()
    return base64.urlsafe_b64encode(digest)


_fernet: Fernet | None = None


def _cipher() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(_derive_key())
    return _fernet


def encrypt_json(payload: dict[str, Any]) -> str:
    return _cipher().encrypt(json.dumps(payload).encode()).decode()


def decrypt_json(token: str) -> dict[str, Any]:
    try:
        raw = _cipher().decrypt(token.encode())
    except InvalidToken as exc:
        raise ValueError("Invalid encrypted payload") from exc
    return json.loads(raw.decode())


def reset_for_tests() -> None:
    """Reset the cached Fernet (used by tests that change the key)."""
    global _fernet
    _fernet = None
