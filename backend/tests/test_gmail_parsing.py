"""Gmail message parsing helpers (no network, fixed payloads)."""
import base64

from app.services.email.gmail import _parse_gmail_message


def _b64(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).decode()


class TestGmailParsing:
    def test_parses_plain_text_message(self):
        payload = {
            "id": "abc123",
            "threadId": "thread-7",
            "payload": {
                "mimeType": "text/plain",
                "headers": [
                    {"name": "From", "value": "Jane Doe <jane@acme.com>"},
                    {"name": "To", "value": "user@gmail.com"},
                    {"name": "Subject", "value": "Re: Hola"},
                    {"name": "Date", "value": "Fri, 02 May 2026 10:00:00 +0000"},
                ],
                "body": {"data": _b64("Hola, gracias por escribir")},
            },
        }
        msg = _parse_gmail_message(payload)
        assert msg.external_id == "abc123"
        assert msg.thread_id == "thread-7"
        assert msg.from_email == "jane@acme.com"
        assert msg.to_email == "user@gmail.com"
        assert msg.subject == "Re: Hola"
        assert msg.body == "Hola, gracias por escribir"

    def test_prefers_text_plain_over_html_in_multipart(self):
        payload = {
            "id": "x",
            "threadId": "t",
            "payload": {
                "mimeType": "multipart/alternative",
                "headers": [
                    {"name": "From", "value": "a@b.com"},
                    {"name": "Subject", "value": "S"},
                ],
                "parts": [
                    {"mimeType": "text/html", "body": {"data": _b64("<p>HTML</p>")}},
                    {"mimeType": "text/plain", "body": {"data": _b64("PLAIN")}},
                ],
            },
        }
        msg = _parse_gmail_message(payload)
        assert msg.body == "PLAIN"

    def test_handles_missing_date_gracefully(self):
        payload = {
            "id": "x",
            "threadId": "t",
            "payload": {
                "mimeType": "text/plain",
                "headers": [{"name": "From", "value": "a@b.com"}],
                "body": {"data": _b64("hi")},
            },
        }
        msg = _parse_gmail_message(payload)
        assert msg.received_at is not None
        assert msg.received_at.tzinfo is not None
