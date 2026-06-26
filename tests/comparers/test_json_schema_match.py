"""Tests for the JSON schema grader comparer."""

import pytest

from src.comparers.json_schema_match import JsonSchemaMatchComparer

SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
    },
    "required": ["answer"],
    "additionalProperties": False,
}


@pytest.mark.asyncio
async def test_json_schema_grader_passes_valid_output() -> None:
    """Valid JSON that matches the schema should pass."""
    grader = JsonSchemaMatchComparer({"name": "shape", "schema": SCHEMA})

    score, passed, details = await grader.compare(expected="", actual='{"answer":"ok"}')

    assert score == 1.0
    assert passed is True
    assert details == {"valid": True}


@pytest.mark.asyncio
async def test_json_schema_grader_fails_invalid_json() -> None:
    """Invalid JSON should fail before schema validation runs."""
    grader = JsonSchemaMatchComparer({"name": "shape", "schema": SCHEMA})

    score, passed, details = await grader.compare(expected="", actual="not json")

    assert score == 0.0
    assert passed is False
    assert details["valid"] is False
    assert "not valid JSON" in details["error"]
    assert "line 1, column 1" in details["error"]
    assert "'n'" in details["error"]
    assert "Output preview: 'not json'" in details["error"]


@pytest.mark.asyncio
async def test_json_schema_grader_fails_schema_validation() -> None:
    """JSON that violates the configured schema should fail."""
    grader = JsonSchemaMatchComparer({"name": "shape", "schema": SCHEMA})

    score, passed, details = await grader.compare(expected="", actual='{"answer": 3}')

    assert score == 0.0
    assert passed is False
    assert details["valid"] is False
    assert details["error"] == "JSON schema validation failed"
    assert details["validation_path"] == "$.answer"
    assert "string" in details["validation_message"]


@pytest.mark.asyncio
async def test_json_schema_grader_supports_score_only_mode() -> None:
    """A null threshold should make the grader informational only."""
    grader = JsonSchemaMatchComparer(
        {"name": "shape", "schema": SCHEMA, "threshold": None},
    )

    score, passed, details = await grader.compare(expected="", actual='{"answer":"ok"}')

    assert score == 1.0
    assert passed is None
    assert details == {"valid": True}


def test_json_schema_grader_requires_schema() -> None:
    """A schema grader without a schema should fail at construction time."""
    with pytest.raises(ValueError, match="requires a schema object"):
        JsonSchemaMatchComparer({"name": "shape"})
