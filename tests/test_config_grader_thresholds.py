"""Tests for grader threshold schema behavior."""

from src.routers.schemas.configs import GraderSchema


def test_grader_schema_omitted_threshold_uses_type_default() -> None:
    """Omitted thresholds preserve the existing default behavior."""
    grader = GraderSchema(name="judge", type="prompt")

    assert grader.threshold == 0.7


def test_grader_schema_null_threshold_is_preserved() -> None:
    """Explicit null thresholds make graders score-only."""
    grader = GraderSchema(name="judge", type="prompt", threshold=None)

    assert grader.threshold is None
