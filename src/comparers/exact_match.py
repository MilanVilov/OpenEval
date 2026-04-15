"""Exact match comparer — strict string equality."""

from src.comparers.base import BaseComparer, register_comparer


@register_comparer("exact_match")
class ExactMatchComparer(BaseComparer):
    """Compare expected and actual outputs for exact string equality.

    Config options:
        case_sensitive (bool): Whether comparison is case-sensitive. Default True.
        strip_whitespace (bool): Whether to strip leading/trailing whitespace. Default True.
    """

    async def compare(self, *, expected: str, actual: str) -> tuple[float, bool, dict]:
        """Return 1.0/True if strings match exactly, 0.0/False otherwise."""
        case_sensitive = self.config.get("case_sensitive", True)
        strip_ws = self.config.get("strip_whitespace", True)

        e = expected.strip() if strip_ws else expected
        a = actual.strip() if strip_ws else actual

        if not case_sensitive:
            e = e.lower()
            a = a.lower()

        matched = e == a
        return (
            1.0 if matched else 0.0,
            matched,
            {"case_sensitive": case_sensitive, "strip_whitespace": strip_ws},
        )
