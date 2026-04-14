"""JSON schema match comparer — validate JSON structure and key values."""

import json

from src.comparers.base import BaseComparer, register_comparer


@register_comparer("json_schema_match")
class JsonSchemaMatchComparer(BaseComparer):
    """Compare expected and actual JSON outputs.

    Parses both as JSON, then checks if all keys in expected exist in actual
    with matching values. Extra keys in actual are allowed.

    Config options:
        strict (bool): If True, actual must have exactly the same keys. Default False.
    """

    async def compare(self, *, expected: str, actual: str) -> tuple[float, bool, dict]:
        """Return score based on matching JSON keys/values."""
        try:
            expected_obj = json.loads(expected)
            actual_obj = json.loads(actual)
        except json.JSONDecodeError as exc:
            return 0.0, False, {"error": f"JSON parse error: {exc}"}

        if not isinstance(expected_obj, dict) or not isinstance(actual_obj, dict):
            # Simple equality for non-dict JSON
            matched = expected_obj == actual_obj
            return (1.0 if matched else 0.0, matched, {"type": "non_dict_comparison"})

        strict = self.config.get("strict", False)

        # Count matching keys
        expected_keys = set(expected_obj.keys())
        actual_keys = set(actual_obj.keys())

        if strict and expected_keys != actual_keys:
            missing = expected_keys - actual_keys
            extra = actual_keys - expected_keys
            return 0.0, False, {"missing_keys": list(missing), "extra_keys": list(extra)}

        matching = 0
        total = len(expected_keys) if expected_keys else 1
        details_keys: dict = {}

        for key in expected_keys:
            if key in actual_obj and actual_obj[key] == expected_obj[key]:
                matching += 1
                details_keys[key] = "match"
            elif key not in actual_obj:
                details_keys[key] = "missing"
            else:
                details_keys[key] = f"mismatch: expected={expected_obj[key]!r}, got={actual_obj[key]!r}"

        score = matching / total
        passed = score >= self.config.get("threshold", 1.0)
        return score, passed, {"key_results": details_keys, "strict": strict}
