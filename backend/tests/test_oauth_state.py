"""Signed OAuth state tokens."""
from datetime import timedelta

import pytest
from freezegun import freeze_time

from app.services.oauth_state import make_state, parse_state


class TestOAuthState:
    def test_roundtrip(self):
        token = make_state(user_id=42, tenant_id=7, provider="gmail")
        ctx = parse_state(token)
        assert ctx == {"user_id": 42, "tenant_id": 7, "provider": "gmail"}

    def test_invalid_state_raises(self):
        with pytest.raises(ValueError):
            parse_state("not-a-jwt")

    def test_expired_state_raises(self):
        with freeze_time("2026-01-01 12:00:00"):
            token = make_state(1, 1, "gmail", ttl_minutes=5)
        with freeze_time("2026-01-01 12:00:00") as frozen:
            frozen.tick(delta=timedelta(minutes=10))
            with pytest.raises(ValueError):
                parse_state(token)
