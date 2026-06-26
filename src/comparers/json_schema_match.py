"""JSON schema grader — validate model output against a configured schema."""

import json
from collections.abc import Sequence

from jsonschema import SchemaError, ValidationError
from jsonschema.validators import validator_for

from src.comparers.base import BaseComparer


class JsonSchemaMatchComparer(BaseComparer):
    """Validate the actual JSON output against the configured schema.

    Config options:
        name (str): Human-readable grader name.
        schema (dict): JSON Schema used to validate the model output.
        threshold (float | None): Minimum score to pass. ``None`` makes the grader informational.
    """

    def __init__(self, config: dict | None = None) -> None:
        super().__init__(config)
        self.grader_name: str = self.config.get("name", "json_schema")
        self.threshold: float | None = self.config.get("threshold", 1.0)
        self.schema = self._load_schema(self.config.get("schema"))
        validator_cls = validator_for(self.schema)
        validator_cls.check_schema(self.schema)
        self._validator = validator_cls(self.schema)

    async def compare(
        self,
        *,
        expected: str,
        actual: str,
        row_data: dict | None = None,
    ) -> tuple[float, bool | None, dict]:
        """Return ``1.0`` when the model output matches the configured schema."""
        del expected, row_data

        actual_object, error = self._parse_json(actual)
        if error is not None:
            return 0.0, self._score_passed(0.0), {"error": error, "valid": False}

        validation_error = self._first_validation_error(actual_object)
        if validation_error is None:
            return 1.0, self._score_passed(1.0), {"valid": True}

        return 0.0, self._score_passed(0.0), self._validation_failure_details(validation_error)

    def _load_schema(self, schema: object) -> dict:
        """Return the configured schema, raising a clear error when missing or invalid."""
        if not isinstance(schema, dict):
            raise ValueError("JSON schema grader requires a schema object")
        try:
            validator_for(schema).check_schema(schema)
        except SchemaError as exc:
            raise ValueError(f"Invalid JSON schema: {exc.message}") from exc
        return schema

    def _parse_json(self, actual: str) -> tuple[object | None, str | None]:
        """Parse the provider output as JSON and return an error message on failure."""
        try:
            return json.loads(actual), None
        except json.JSONDecodeError as exc:
            return None, _build_parse_error_message(actual, exc)

    def _first_validation_error(self, actual_object: object) -> ValidationError | None:
        """Return the first schema validation error, if any."""
        errors = sorted(self._validator.iter_errors(actual_object), key=_validation_error_sort_key)
        return errors[0] if errors else None

    def _validation_failure_details(self, error: ValidationError) -> dict:
        """Convert a validation error into stable grader details."""
        return {
            "error": "JSON schema validation failed",
            "valid": False,
            "validation_message": error.message,
            "validation_path": _format_path(error.path),
            "schema_path": _format_path(error.schema_path),
        }

    def _score_passed(self, score: float) -> bool | None:
        """Return the threshold judgment for a score, if configured."""
        if self.threshold is None:
            return None
        return score >= self.threshold


def _validation_error_sort_key(error: ValidationError) -> tuple[str, str]:
    """Return a deterministic sort key for validation errors."""
    return _format_path(error.path), _format_path(error.schema_path)


def _format_path(path: Sequence[object]) -> str:
    """Return a JSONPath-like string for response or schema error paths."""
    if not path:
        return "$"

    formatted = "$"
    for part in path:
        if isinstance(part, int):
            formatted += f"[{part}]"
            continue
        formatted += f".{part}"
    return formatted


def _build_parse_error_message(actual: str, error: json.JSONDecodeError) -> str:
    """Return a descriptive parse error message for non-JSON outputs."""
    preview = _output_preview(actual)
    first_token = _first_non_whitespace_character(actual)
    first_token_note = (
        f" The first non-whitespace character was {first_token!r}."
        if first_token is not None
        else " The response was empty or whitespace only."
    )
    return (
        "The model output was not valid JSON, so the JSON schema grader could not validate it. "
        f"JSON parsing failed at line {error.lineno}, column {error.colno}: {error.msg}."
        f"{first_token_note} Output preview: {preview}"
    )


def _output_preview(actual: str, *, limit: int = 160) -> str:
    """Return a compact preview of the raw model output."""
    normalized = " ".join(actual.split())
    if not normalized:
        return "(empty response)"
    if len(normalized) <= limit:
        return repr(normalized)
    return repr(f"{normalized[:limit].rstrip()}...")


def _first_non_whitespace_character(actual: str) -> str | None:
    """Return the first non-whitespace character in the output, if any."""
    stripped = actual.lstrip()
    if not stripped:
        return None
    return stripped[0]
