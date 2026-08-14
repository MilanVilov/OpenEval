"""Tests for evaluation run API response serialization."""

from types import SimpleNamespace

from src.routers.runs import _run_to_response


def test_run_response_exposes_run_flex_setting() -> None:
    """A run response should identify when that run uses Flex processing."""
    run = SimpleNamespace(
        id="run-id",
        eval_config_id="config-id",
        dataset_id="dataset-id",
        status="running",
        progress=1,
        total_rows=2,
        summary=None,
        error_message=None,
        started_at=None,
        completed_at=None,
        created_at="2026-08-14T10:00:00Z",
        flex_enabled=True,
        config=SimpleNamespace(name="Config"),
        dataset=SimpleNamespace(name="Dataset"),
    )

    response = _run_to_response(run)

    assert response.flex_enabled is True
