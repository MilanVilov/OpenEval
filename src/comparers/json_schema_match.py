"""JSON schema grader — validate JSON structure and key values."""

import json

from src.comparers.base import BaseComparer


class JsonSchemaMatchComparer(BaseComparer):
    """Compare expected and actual JSON outputs.

    Parses both as JSON, then checks if all keys in expected exist in actual
    with matching values. Extra keys in actual are allowed.

    Config options:
        name (str): Human-readable grader name.
        strict (bool): If True, actual must have exactly the same keys. Default False.
        threshold (float | None): Minimum score to pass. ``None`` makes the grader informational.
    """

    def __init__(self, config: dict | None = None) -> None:
        super().__init__(config)
        self.grader_name: str = self.config.get("name", "json_schema")
        self.strict: bool = self.config.get("strict", False)
        self.threshold: float | None = self.config.get("threshold", 1.0)

    async def compare(
        self,
        *,
        expected: str,
        actual: str,
        row_data: dict | None = None,
    ) -> tuple[float, bool | None, dict]:
        """Return score based on matching JSON keys/values."""
        try:
            expected_obj = json.loads(expected)
            actual_obj = json.loads(actual)
        except json.JSONDecodeError as exc:
            return 0.0, self._score_passed(0.0), {"error": f"JSON parse error: {exc}"}

        if not isinstance(expected_obj, dict) or not isinstance(actual_obj, dict):
            # Simple equality for non-dict JSON
            matched = expected_obj == actual_obj
            score = 1.0 if matched else 0.0
            return score, self._score_passed(score), {"type": "non_dict_comparison"}

        strict = self.strict

        # Count matching keys
        expected_keys = set(expected_obj.keys())
        actual_keys = set(actual_obj.keys())

        if strict and expected_keys != actual_keys:
            missing = expected_keys - actual_keys
            extra = actual_keys - expected_keys
            return (
                0.0,
                self._score_passed(0.0),
                {"missing_keys": list(missing), "extra_keys": list(extra)},
            )

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
                expected_value = expected_obj[key]
                actual_value = actual_obj[key]
                details_keys[key] = (
                    f"mismatch: expected={expected_value!r}, got={actual_value!r}"
                )

        score = matching / total
        passed = self._score_passed(score)
        return score, passed, {"key_results": details_keys, "strict": strict}

    def _score_passed(self, score: float) -> bool | None:
        """Return the threshold judgment for a score, if configured."""
        if self.threshold is None:
            return None
        return score >= self.threshold
