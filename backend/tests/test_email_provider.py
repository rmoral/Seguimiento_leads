"""Provider registry."""
import pytest

from app.services.email import get_provider
from app.services.email.factory import supported_providers
from app.services.email.gmail import GmailProvider


class TestProviderFactory:
    def test_gmail_is_supported(self):
        assert "gmail" in supported_providers()

    def test_get_provider_returns_instance(self):
        prov = get_provider("gmail")
        assert isinstance(prov, GmailProvider)

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError):
            get_provider("yahoo")
