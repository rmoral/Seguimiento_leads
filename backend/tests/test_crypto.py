"""Token encryption (Fernet wrapper)."""
import pytest

from app.services.crypto import decrypt_json, encrypt_json


class TestCrypto:
    def test_roundtrip(self):
        payload = {"token": "abc", "refresh": "xyz", "scopes": ["a", "b"]}
        cipher = encrypt_json(payload)
        assert isinstance(cipher, str)
        assert payload == decrypt_json(cipher)

    def test_ciphertext_is_not_plaintext(self):
        cipher = encrypt_json({"token": "supersecret"})
        assert "supersecret" not in cipher

    def test_invalid_cipher_raises(self):
        with pytest.raises(ValueError):
            decrypt_json("not-a-valid-token")
