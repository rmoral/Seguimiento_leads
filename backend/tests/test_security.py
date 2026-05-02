"""Unit tests for security primitives (hashing + JWT)."""
from datetime import timedelta

import pytest
from freezegun import freeze_time

from app.core.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        hashed = hash_password("supersecret")
        assert hashed != "supersecret"
        assert len(hashed) > 20

    def test_hash_is_salted(self):
        # Same password produces different hashes thanks to salt
        a = hash_password("supersecret")
        b = hash_password("supersecret")
        assert a != b

    def test_verify_correct_password(self):
        hashed = hash_password("supersecret")
        assert verify_password("supersecret", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("supersecret")
        assert verify_password("wrong", hashed) is False


class TestJWT:
    def test_token_roundtrip(self):
        token = create_access_token(subject=42, extra={"tid": 7})
        payload = decode_token(token)
        assert payload["sub"] == "42"
        assert payload["tid"] == 7
        assert "exp" in payload

    def test_token_subject_is_stringified(self):
        token = create_access_token(subject=123)
        payload = decode_token(token)
        assert payload["sub"] == "123"

    def test_invalid_token_raises(self):
        with pytest.raises(ValueError):
            decode_token("not-a-real-jwt")

    def test_tampered_token_raises(self):
        token = create_access_token(subject=1)
        # Flip a character to invalidate the signature
        tampered = token[:-2] + ("AB" if token[-2:] != "AB" else "CD")
        with pytest.raises(ValueError):
            decode_token(tampered)

    def test_expired_token_raises(self):
        with freeze_time("2026-01-01 12:00:00"):
            token = create_access_token(subject=1)
        # Jump well past the expiration window
        with freeze_time("2026-01-01 12:00:00") as frozen:
            frozen.tick(delta=timedelta(hours=24))
            with pytest.raises(ValueError):
                decode_token(token)
