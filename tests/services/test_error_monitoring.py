"""Tests for Sentry initialization and handled-exception reporting."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from sentry_sdk.integrations.logging import LoggingIntegration

from src.services.error_monitoring import init_sentry, report_exception


def test_init_sentry_skips_when_dsn_missing() -> None:
    """Sentry should stay disabled when no DSN is configured."""
    settings = SimpleNamespace(
        sentry_dsn="",
        sentry_environment="test",
        sentry_release="release-1",
        sentry_traces_sample_rate=0.5,
    )

    with patch("src.services.error_monitoring.sentry_sdk.init") as mock_init:
        init_sentry(settings)

    mock_init.assert_not_called()


def test_init_sentry_configures_sdk() -> None:
    """Sentry should initialize with breadcrumb-only logging integration."""
    settings = SimpleNamespace(
        sentry_dsn="https://public@example.com/1",
        sentry_environment="test",
        sentry_release="release-1",
        sentry_traces_sample_rate=0.25,
    )

    with patch("src.services.error_monitoring.sentry_sdk.init") as mock_init:
        init_sentry(settings)

    kwargs = mock_init.call_args.kwargs
    assert kwargs["dsn"] == "https://public@example.com/1"
    assert kwargs["environment"] == "test"
    assert kwargs["release"] == "release-1"
    assert kwargs["traces_sample_rate"] == 0.25
    assert kwargs["disabled_integrations"] == [LoggingIntegration]
    assert len(kwargs["integrations"]) == 1
    assert isinstance(kwargs["integrations"][0], LoggingIntegration)
    assert kwargs["integrations"][0]._handler is None


def test_report_exception_normalizes_tags_and_contexts() -> None:
    """Handled exception reports should normalize Sentry metadata."""
    error = RuntimeError("boom")

    with (
        patch("src.services.error_monitoring.sentry_sdk.is_initialized", return_value=True),
        patch("src.services.error_monitoring.sentry_sdk.capture_exception") as mock_capture,
    ):
        report_exception(
            error,
            tags={"stage": "run_evaluation", "attempt": 2},
            contexts={
                "run": {
                    "id": "run1",
                    "path": Path("/tmp/run.csv"),
                    "values": [1, True],
                }
            },
            extras={"debug": False},
        )

    assert mock_capture.call_args.args == (error,)
    assert mock_capture.call_args.kwargs["tags"] == {
        "stage": "run_evaluation",
        "attempt": "2",
    }
    assert mock_capture.call_args.kwargs["contexts"] == {
        "run": {
            "id": "run1",
            "path": "/tmp/run.csv",
            "values": [1, True],
        }
    }
    assert mock_capture.call_args.kwargs["extras"] == {"debug": False}
