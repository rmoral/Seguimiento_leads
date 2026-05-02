"""Provider lookup. Add new providers (Outlook, SMTP) here."""
from __future__ import annotations

from app.services.email.base import EmailProvider
from app.services.email.gmail import GmailProvider

_REGISTRY: dict[str, type[EmailProvider]] = {
    "gmail": GmailProvider,
}


def get_provider(name: str) -> EmailProvider:
    try:
        return _REGISTRY[name]()
    except KeyError as exc:
        raise ValueError(f"Unknown email provider: {name!r}") from exc


def supported_providers() -> list[str]:
    return list(_REGISTRY)
