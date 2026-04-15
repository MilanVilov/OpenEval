"""Base comparer interface and registration."""

from abc import ABC, abstractmethod

# Registry of comparer classes keyed by name
_COMPARER_REGISTRY: dict[str, type["BaseComparer"]] = {}


def register_comparer(name: str):
    """Class decorator to register a comparer under the given name."""
    def decorator(cls: type["BaseComparer"]) -> type["BaseComparer"]:
        _COMPARER_REGISTRY[name] = cls
        return cls
    return decorator


class BaseComparer(ABC):
    """Abstract base class for result comparers."""

    def __init__(self, config: dict | None = None) -> None:
        self.config = config or {}

    @abstractmethod
    async def compare(
        self,
        *,
        expected: str,
        actual: str,
        row_data: dict | None = None,
    ) -> tuple[float, bool, dict]:
        """Compare expected and actual outputs.

        Args:
            expected: The expected output string.
            actual: The actual output string produced by the LLM.
            row_data: The full CSV row dict for the current item (optional).

        Returns:
            Tuple of (score, passed, details):
            - score: float between 0.0 and 1.0
            - passed: whether the comparison passed
            - details: dict with additional comparison info
        """
        ...
