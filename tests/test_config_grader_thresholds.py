"""Tests for grader threshold schema behavior."""

import pytest
from pydantic import ValidationError

from src.routers.schemas.configs import GraderSchema


def test_grader_schema_omitted_threshold_uses_type_default() -> None:
    """Omitted thresholds preserve the existing default behavior."""
    grader = GraderSchema(name="judge", type="prompt")

    assert grader.threshold == 0.7


def test_grader_schema_null_threshold_is_preserved() -> None:
    """Explicit null thresholds make graders score-only."""
    grader = GraderSchema(name="judge", type="prompt", threshold=None)

    assert grader.threshold is None


def test_json_schema_grader_requires_schema() -> None:
    """Schema graders must define the schema they validate against."""
    with pytest.raises(ValidationError, match="JSON schema graders require a schema"):
        GraderSchema(name="shape", type="json_schema")


def test_json_schema_grader_rejects_invalid_schema() -> None:
    """Schema graders reject malformed JSON Schema definitions."""
    with pytest.raises(ValidationError, match="Invalid JSON schema"):
        GraderSchema(name="shape", type="json_schema", schema={"type": "not-a-real-type"})
