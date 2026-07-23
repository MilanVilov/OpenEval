"""Sentry initialization and handled-exception reporting helpers."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

from src.config import Settings

logger = logging.getLogger(__name__)


def init_sentry(settings: Settings) -> None:
    """Initialize Sentry when a DSN is configured."""
    dsn = _as_nonempty_string(getattr(settings, "sentry_dsn", ""))
    if dsn is None:
        return

    try:
        sentry_sdk.init(
            dsn=dsn,
            environment=_as_nonempty_string(getattr(settings, "sentry_environment", "")),
            release=_as_nonempty_string(getattr(settings, "sentry_release", "")),
            traces_sample_rate=_as_sample_rate(
                getattr(settings, "sentry_traces_sample_rate", 0.0)
            ),
            integrations=[LoggingIntegration(level=logging.INFO, event_level=None)],
            disabled_integrations=[LoggingIntegration],
        )
    except Exception:
        logger.exception("Failed to initialize Sentry")


def report_exception(
    exc: Exception,
    *,
    tags: Mapping[str, object] | None = None,
    contexts: Mapping[str, Mapping[str, object]] | None = None,
    extras: Mapping[str, object] | None = None,
) -> None:
    """Send one handled exception to Sentry with normalized metadata."""
    if not sentry_sdk.is_initialized():
        return

    try:
        sentry_sdk.capture_exception(
            exc,
            tags=_normalize_tags(tags),
            contexts=_normalize_contexts(contexts),
            extras=_normalize_mapping(extras),
        )
    except Exception:
        logger.exception("Failed to report exception to Sentry")


def _normalize_tags(tags: Mapping[str, object] | None) -> dict[str, str] | None:
    """Return Sentry tag values coerced to strings."""
    if not tags:
        return None
    return {str(key): str(value) for key, value in tags.items() if value is not None}


def _normalize_contexts(
    contexts: Mapping[str, Mapping[str, object]] | None,
) -> dict[str, dict[str, Any]] | None:
    """Return normalized Sentry contexts."""
    if not contexts:
        return None
    return {str(key): _normalize_mapping(value) or {} for key, value in contexts.items() if value}


def _normalize_mapping(values: Mapping[str, object] | None) -> dict[str, Any] | None:
    """Return one normalized mapping with JSON-friendly values."""
    if not values:
        return None
    return {
        str(key): _normalize_value(value) for key, value in values.items() if value is not None
    }


def _normalize_value(value: object) -> Any:
    """Return one value normalized for safe Sentry serialization."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {
            str(key): _normalize_value(item) for key, item in value.items() if item is not None
        }
    if isinstance(value, (list, tuple, set)):
        return [_normalize_value(item) for item in value]
    return str(value)


def _as_nonempty_string(value: object) -> str | None:
    """Return one stripped string setting or ``None`` when unset."""
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _as_sample_rate(value: object) -> float:
    """Return one bounded Sentry sample rate."""
    if isinstance(value, (int, float)):
        return min(max(float(value), 0.0), 1.0)
    return 0.0
