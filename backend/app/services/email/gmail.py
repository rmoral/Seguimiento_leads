"""Gmail implementation of EmailProvider.

Uses google-auth + google-api-python-client. The Gmail API client is built
lazily so unit tests can patch `_build_service` without needing real
credentials.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
from email.message import EmailMessage as MIMEMessage
from email.utils import parseaddr, parsedate_to_datetime
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app.core.config import settings
from app.services.email.base import EmailMessage, EmailProvider

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]


def _client_config() -> dict[str, Any]:
    return {
        "web": {
            "client_id": settings.GMAIL_CLIENT_ID,
            "client_secret": settings.GMAIL_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.GMAIL_REDIRECT_URI],
        }
    }


class GmailProvider(EmailProvider):
    name = "gmail"

    # ---------- OAuth ----------

    def authorization_url(self, state: str) -> str:
        flow = Flow.from_client_config(
            _client_config(), scopes=GMAIL_SCOPES, state=state
        )
        flow.redirect_uri = settings.GMAIL_REDIRECT_URI
        url, _ = flow.authorization_url(
            access_type="offline", include_granted_scopes="true", prompt="consent"
        )
        return url

    def exchange_code(self, code: str) -> tuple[str, dict[str, Any]]:
        flow = Flow.from_client_config(_client_config(), scopes=GMAIL_SCOPES)
        flow.redirect_uri = settings.GMAIL_REDIRECT_URI
        flow.fetch_token(code=code)
        creds: Credentials = flow.credentials
        email = self._whoami(creds)
        return email, _credentials_to_dict(creds)

    # ---------- Messaging ----------

    def send_message(
        self,
        tokens: dict[str, Any],
        from_email: str,
        to: str,
        subject: str,
        body: str,
    ) -> str:
        creds = _credentials_from_dict(tokens)
        service = self._build_service(creds)
        msg = MIMEMessage()
        msg["To"] = to
        msg["From"] = from_email
        msg["Subject"] = subject
        msg.set_content(body)
        encoded = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        sent = (
            service.users()
            .messages()
            .send(userId="me", body={"raw": encoded})
            .execute()
        )
        return sent["id"]

    def fetch_messages(
        self,
        tokens: dict[str, Any],
        since: datetime | None = None,
        max_results: int = 50,
    ) -> list[EmailMessage]:
        creds = _credentials_from_dict(tokens)
        service = self._build_service(creds)

        query = "in:inbox"
        if since is not None:
            query += f" after:{int(since.timestamp())}"

        listing = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results)
            .execute()
        )
        ids = [m["id"] for m in listing.get("messages", [])]

        out: list[EmailMessage] = []
        for mid in ids:
            payload = (
                service.users()
                .messages()
                .get(userId="me", id=mid, format="full")
                .execute()
            )
            out.append(_parse_gmail_message(payload))
        return out

    # ---------- Helpers ----------

    def _build_service(self, creds: Credentials):
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        return build("gmail", "v1", credentials=creds, cache_discovery=False)

    def _whoami(self, creds: Credentials) -> str:
        service = self._build_service(creds)
        profile = service.users().getProfile(userId="me").execute()
        return profile["emailAddress"]


# ---------- Token (de)serialisation ----------


def _credentials_to_dict(creds: Credentials) -> dict[str, Any]:
    return {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes or []),
    }


def _credentials_from_dict(data: dict[str, Any]) -> Credentials:
    return Credentials(
        token=data.get("token"),
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri"),
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
        scopes=data.get("scopes"),
    )


# ---------- Gmail message parsing ----------


def _header(headers: list[dict[str, str]], name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def _decode_part(part: dict[str, Any]) -> str:
    data = part.get("body", {}).get("data")
    if not data:
        return ""
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")


def _extract_body(payload: dict[str, Any]) -> str:
    mime = payload.get("mimeType", "")
    if mime.startswith("text/"):
        return _decode_part(payload)
    for part in payload.get("parts", []) or []:
        # Prefer text/plain over text/html when both exist
        if part.get("mimeType") == "text/plain":
            return _decode_part(part)
    for part in payload.get("parts", []) or []:
        if part.get("mimeType", "").startswith("text/"):
            return _decode_part(part)
        nested = _extract_body(part)
        if nested:
            return nested
    return ""


def _parse_gmail_message(msg: dict[str, Any]) -> EmailMessage:
    payload = msg.get("payload", {})
    headers = payload.get("headers", [])
    _, from_email = parseaddr(_header(headers, "From"))
    _, to_email = parseaddr(_header(headers, "To"))
    subject = _header(headers, "Subject")

    date_str = _header(headers, "Date")
    try:
        received = parsedate_to_datetime(date_str) if date_str else datetime.now(timezone.utc)
    except (TypeError, ValueError):
        received = datetime.now(timezone.utc)
    if received.tzinfo is None:
        received = received.replace(tzinfo=timezone.utc)

    return EmailMessage(
        external_id=msg["id"],
        thread_id=msg.get("threadId"),
        from_email=from_email or "",
        to_email=to_email or None,
        subject=subject,
        body=_extract_body(payload),
        received_at=received,
    )
