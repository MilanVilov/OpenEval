"""Pattern match comparer — check if actual output contains expected text or matches a regex."""

import re

from src.comparers.base import BaseComparer, register_comparer


@register_comparer("pattern_match")
class PatternMatchComparer(BaseComparer):
    """Compare using substring containment or regex pattern matching.

    Config options:
        mode (str): "contains" or "regex". Default "contains".
        case_sensitive (bool): Whether matching is case-sensitive. Default False.
    """

    async def compare(self, *, expected: str, actual: str, row_data: dict | None = None) -> tuple[float, bool, dict]:
        """Return 1.0/True if actual matches the expected pattern."""
        mode = self.config.get("mode", "contains")
        case_sensitive = self.config.get("case_sensitive", False)

        if mode == "regex":
            flags = 0 if case_sensitive else re.IGNORECASE
            matched = bool(re.search(expected, actual, flags))
        else:
            # Contains mode
            e = expected if case_sensitive else expected.lower()
            a = actual if case_sensitive else actual.lower()
            matched = e in a

        return (
            1.0 if matched else 0.0,
            matched,
            {"mode": mode, "case_sensitive": case_sensitive},
        )
