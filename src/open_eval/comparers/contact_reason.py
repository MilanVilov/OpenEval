"""Contact reason comparer — extracts 'key' from JSON response and compares."""

import json

from open_eval.comparers.base import BaseComparer, register_comparer


@register_comparer("contact_reason")
class ContactReasonComparer(BaseComparer):
    """Compare expected output against the 'key' field from a JSON LLM response.

    The LLM is expected to return a JSON object like:
        {"reasoning": "...", "confidence": 92, "key": "account_issues.account_closure_request"}

    This comparer extracts the 'key' value and does exact string matching
    against the expected output.

    Config options:
        case_sensitive (bool): Whether comparison is case-sensitive. Default False.
        strip_whitespace (bool): Whether to strip whitespace. Default True.
        key_field (str): JSON field to extract. Default "key".
    """

    async def compare(self, *, expected: str, actual: str) -> tuple[float, bool, dict]:
        """Return 1.0/True if the extracted key matches expected, 0.0/False otherwise."""
        case_sensitive = self.config.get("case_sensitive", False)
        strip_ws = self.config.get("strip_whitespace", True)
        key_field = self.config.get("key_field", "key")

        # Parse JSON from actual output
        try:
            parsed = json.loads(actual)
        except (json.JSONDecodeError, TypeError):
            return (
                0.0,
                False,
                {"error": "Failed to parse actual output as JSON", "raw": actual},
            )

        # Extract the key field
        if not isinstance(parsed, dict) or key_field not in parsed:
            return (
                0.0,
                False,
                {"error": f"Field '{key_field}' not found in response", "parsed": parsed},
            )

        extracted = str(parsed[key_field])
        e = expected.strip() if strip_ws else expected
        a = extracted.strip() if strip_ws else extracted

        if not case_sensitive:
            e = e.lower()
            a = a.lower()

        matched = e == a
        details: dict = {
            "expected": expected,
            "extracted_key": extracted,
            "key_field": key_field,
        }

        # Include extra fields from the response for context
        if isinstance(parsed, dict):
            if "confidence" in parsed:
                details["confidence"] = parsed["confidence"]
            if "reasoning" in parsed:
                details["reasoning"] = parsed["reasoning"]

        return (1.0 if matched else 0.0, matched, details)
