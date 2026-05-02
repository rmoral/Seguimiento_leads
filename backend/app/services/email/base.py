"""Provider-agnostic email interface.

A provider knows how to:
- Build the OAuth URL the user must visit to grant access.
- Exchange an authorization code for tokens.
- Send a message on behalf of the connected account.
- Fetch incoming messages since a given timestamp.

Each implementation receives the encrypted-at-rest token JSON when it
needs to operate, so the rest of the application stays oblivious to
provider quirks.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class EmailMessage:
    """Provider-neutral representation of an inbound message."""

    external_id: str  # provider-specific message id (used for dedup)
    thread_id: str | None
    from_email: str
    to_email: str | None
    subject: str
    body: str
    received_at: datetime


class EmailProvider(ABC):
    name: str = "base"

    @abstractmethod
    def authorization_url(self, state: str) -> str:
        """Return the URL the user must visit to grant access."""

    @abstractmethod
    def exchange_code(self, code: str) -> tuple[str, dict[str, Any]]:
        """Exchange an OAuth code for (account_email, token_payload)."""

    @abstractmethod
    def send_message(
        self,
        tokens: dict[str, Any],
        from_email: str,
        to: str,
        subject: str,
        body: str,
    ) -> str:
        """Send a message and return the provider message id."""

    @abstractmethod
    def fetch_messages(
        self,
        tokens: dict[str, Any],
        since: datetime | None = None,
        max_results: int = 50,
    ) -> list[EmailMessage]:
        """Return messages received since `since` (None = latest batch)."""
