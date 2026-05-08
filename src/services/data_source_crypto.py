"""Encryption helpers for remote data source secrets."""

from __future__ import annotations

import json

from cryptography.fernet import Fernet, InvalidToken

from src.config import get_settings


def _get_fernet() -> Fernet:
    """Return the Fernet instance for data source secret encryption."""
    key = get_settings().data_source_encryption_key.strip()
    if not key:
        raise ValueError("DATA_SOURCE_ENCRYPTION_KEY must be set")
    try:
        return Fernet(key.encode("utf-8"))
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "DATA_SOURCE_ENCRYPTION_KEY must be a valid Fernet key",
        ) from exc


def encrypt_secret_payload(payload: dict[str, object]) -> str | None:
    """Encrypt a secret payload, returning ``None`` when it is effectively empty."""
    cleaned = {
        key: value
        for key, value in payload.items()
        if value not in (None, "", {}, [])
    }
    if not cleaned:
        return None
    content = json.dumps(cleaned, sort_keys=True).encode("utf-8")
    return _get_fernet().encrypt(content).decode("utf-8")


def decrypt_secret_payload(encrypted_payload: str | None) -> dict[str, object]:
    """Decrypt a secret payload into a dictionary."""
    if not encrypted_payload:
        return {}
    try:
        decrypted = _get_fernet().decrypt(encrypted_payload.encode("utf-8"))
    except InvalidToken as exc:
        raise ValueError("Failed to decrypt data source secrets") from exc

    payload = json.loads(decrypted.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Decrypted data source secrets must be a JSON object")
    return payload
