"""JSON field grader — recursively finds a field in JSON and compares its value."""

import json
from typing import Any

from src.comparers.base import BaseComparer


def _find_field(obj: Any, field_name: str) -> tuple[bool, Any]:
    """Recursively search through a JSON structure for the first matching field.

    Performs a breadth-first search across dict keys, then recurses into
    nested dicts and lists.

    Returns:
        (found, value) — True and the value if found, False and None otherwise.
    """
    if isinstance(obj, dict):
        if field_name in obj:
            return True, obj[field_name]
        for value in obj.values():
            found, result = _find_field(value, field_name)
            if found:
                return True, result
    elif isinstance(obj, list):
        for item in obj:
            found, result = _find_field(item, field_name)
            if found:
                return True, result
    return False, None


class JsonFieldMatchComparer(BaseComparer):
    """Compare expected output against a named field extracted from a JSON LLM response.

    Recursively searches through all levels of the JSON structure to find the
    first attribute matching the configured field name, then compares its
    string value against the expected output.

    Config options:
        name (str): Human-readable grader name.
        field_name (str): JSON field to search for. Default "key".
        case_sensitive (bool): Whether comparison is case-sensitive. Default False.
        strip_whitespace (bool): Whether to strip whitespace. Default True.
        threshold (float | None): Minimum score to pass. ``None`` makes the grader informational.
    """

    def __init__(self, config: dict | None = None) -> None:
        super().__init__(config)
        self.grader_name: str = self.config.get("name", "json_field")
        self.threshold: float | None = self.config.get("threshold", 0.7)

    async def compare(
        self,
        *,
        expected: str,
        actual: str,
        row_data: dict | None = None,
    ) -> tuple[float, bool | None, dict]:
        """Return the extracted field match score and threshold judgment."""
        case_sensitive = self.config.get("case_sensitive", False)
        strip_ws = self.config.get("strip_whitespace", True)
        field_name = self.config.get("field_name", "key")

        # Parse JSON from actual output
        try:
            parsed = json.loads(actual)
        except (json.JSONDecodeError, TypeError):
            return (
                0.0,
                self._score_passed(0.0),
                {
                    "error": "Failed to parse actual output as JSON",
                    "raw": actual,
                    "threshold": self.threshold,
                },
            )

        # Recursively search for the field
        found, extracted_value = _find_field(parsed, field_name)
        if not found:
            return (
                0.0,
                self._score_passed(0.0),
                {
                    "error": f"Field '{field_name}' not found in response",
                    "parsed": parsed,
                    "threshold": self.threshold,
                },
            )

        extracted = str(extracted_value)
        e = expected.strip() if strip_ws else expected
        a = extracted.strip() if strip_ws else extracted

        if not case_sensitive:
            e = e.lower()
            a = a.lower()

        matched = e == a
        details: dict = {
            "expected": expected,
            "extracted_value": extracted,
            "field_name": field_name,
            "threshold": self.threshold,
        }

        score = 1.0 if matched else 0.0
        return score, self._score_passed(score), details

    def _score_passed(self, score: float) -> bool | None:
        """Return the threshold judgment for a score, if configured."""
        if self.threshold is None:
            return None
        return score >= self.threshold
