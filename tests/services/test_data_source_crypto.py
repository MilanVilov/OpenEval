"""Tests for remote data source secret encryption helpers."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet

from src.services.data_source_crypto import (
    decrypt_secret_payload,
    encrypt_secret_payload,
)


def test_encrypt_and_decrypt_secret_payload_round_trip() -> None:
    """Secret payloads should round-trip through Fernet encryption."""
    settings = SimpleNamespace(data_source_encryption_key=Fernet.generate_key().decode("utf-8"))

    with patch("src.services.data_source_crypto.get_settings", return_value=settings):
        encrypted = encrypt_secret_payload(
            {
                "bearer_token": "secret-token",
                "secret_headers": {"X-Api-Key": "123"},
            }
        )
        decrypted = decrypt_secret_payload(encrypted)

    assert encrypted is not None
    assert decrypted["bearer_token"] == "secret-token"
    assert decrypted["secret_headers"] == {"X-Api-Key": "123"}


def test_encrypt_secret_payload_requires_key() -> None:
    """Missing encryption key should raise a clear error."""
    settings = SimpleNamespace(data_source_encryption_key="")

    with patch("src.services.data_source_crypto.get_settings", return_value=settings):
        with pytest.raises(ValueError, match="DATA_SOURCE_ENCRYPTION_KEY must be set"):
            encrypt_secret_payload({"bearer_token": "secret-token"})
