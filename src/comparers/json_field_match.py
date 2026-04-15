"""JSON field match comparer — recursively finds a field in JSON and compares its value."""

import json
from typing import Any

from src.comparers.base import BaseComparer, register_comparer


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


@register_comparer("json_field_match")
class JsonFieldMatchComparer(BaseComparer):
    """Compare expected output against a named field extracted from a JSON LLM response.

    Recursively searches through all levels of the JSON structure to find the
    first attribute matching the configured field name, then compares its
    string value against the expected output.

    Example — given a response like:
        {"result": {"reasoning": "...", "answer": "Paris"}}
    and field_name="answer", the comparer extracts "Paris" and compares it.

    Config options:
        field_name (str): JSON field to search for. Default "key".
        case_sensitive (bool): Whether comparison is case-sensitive. Default False.
        strip_whitespace (bool): Whether to strip whitespace. Default True.
    """

    async def compare(self, *, expected: str, actual: str, row_data: dict | None = None) -> tuple[float, bool, dict]:
        """Return 1.0/True if the extracted field value matches expected, 0.0/False otherwise."""
        case_sensitive = self.config.get("case_sensitive", False)
        strip_ws = self.config.get("strip_whitespace", True)
        field_name = self.config.get("field_name", "key")

        # Parse JSON from actual output
        try:
            parsed = json.loads(actual)
        except (json.JSONDecodeError, TypeError):
            return (
                0.0,
                False,
                {"error": "Failed to parse actual output as JSON", "raw": actual},
            )

        # Recursively search for the field
        found, extracted_value = _find_field(parsed, field_name)
        if not found:
            return (
                0.0,
                False,
                {"error": f"Field '{field_name}' not found in response", "parsed": parsed},
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
        }

        return (1.0 if matched else 0.0, matched, details)
