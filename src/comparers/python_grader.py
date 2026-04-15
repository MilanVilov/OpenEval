"""Python grader — execute user-defined ``grade(sample, item)`` functions.

The user supplies a Python source string that must define a ``grade``
function with signature ``(sample: dict, item: dict) -> float``.

* ``sample`` — ``{"output_text": <LLM output>}``
* ``item`` — the full CSV row dict

The returned float is clamped to 0.0–1.0 and compared against the
configured threshold.

Config keys (passed via ``config`` dict):
    name (str): Human-readable grader name.
    source_code (str): Python source defining ``grade(sample, item) -> float``.
    threshold (float): Minimum score to pass. Default ``0.7``.
"""

import logging
import json
import math
import re

from src.comparers.base import BaseComparer

logger = logging.getLogger(__name__)

# Builtins allowed inside user code.  Dangerous names like __import__,
# open, exec, eval, compile, globals, locals are excluded.
_SAFE_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "filter": filter,
    "float": float,
    "frozenset": frozenset,
    "int": int,
    "isinstance": isinstance,
    "len": len,
    "list": list,
    "map": map,
    "max": max,
    "min": min,
    "print": print,
    "range": range,
    "reversed": reversed,
    "round": round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "type": type,
    "zip": zip,
    "True": True,
    "False": False,
    "None": None,
}

# Pre-imported modules available to user code.
_ALLOWED_MODULES = {
    "re": re,
    "json": json,
    "math": math,
}


def _safe_import(name: str, *args: object, **kwargs: object) -> object:
    """Restricted __import__ that only allows pre-approved modules."""
    if name in _ALLOWED_MODULES:
        return _ALLOWED_MODULES[name]
    raise ImportError(f"Import of '{name}' is not allowed. Available modules: {', '.join(sorted(_ALLOWED_MODULES))}")


class PythonGraderComparer(BaseComparer):
    """Execute a user-defined Python ``grade`` function to score outputs."""

    def __init__(self, config: dict | None = None) -> None:
        super().__init__(config)
        self.grader_name: str = self.config.get("name", "python_grader")
        self.source_code: str = self.config.get("source_code", "")
        self.threshold: float = self.config.get("threshold", 0.7)

    async def compare(
        self,
        *,
        expected: str,
        actual: str,
        row_data: dict | None = None,
    ) -> tuple[float, bool, dict]:
        """Compile and run the user ``grade`` function, returning its score."""
        sample = {"output_text": actual}
        item = dict(row_data) if row_data else {}

        exec_globals: dict = {
            "__builtins__": {**_SAFE_BUILTINS, "__import__": _safe_import},
            **_ALLOWED_MODULES,
        }

        try:
            exec(self.source_code, exec_globals)  # noqa: S102 — intentional user code execution
        except Exception as exc:
            logger.warning("Python grader %s: compile/exec error: %s", self.grader_name, exc)
            return 0.0, False, {
                "grader_name": self.grader_name,
                "threshold": self.threshold,
                "error": f"Execution error: {exc}",
            }

        grade_fn = exec_globals.get("grade")
        if not callable(grade_fn):
            return 0.0, False, {
                "grader_name": self.grader_name,
                "threshold": self.threshold,
                "error": "Source code must define a callable 'grade(sample, item)' function.",
            }

        try:
            raw_score = grade_fn(sample, item)
            score = max(0.0, min(1.0, float(raw_score)))
        except Exception as exc:
            logger.warning("Python grader %s: grade() error: %s", self.grader_name, exc)
            return 0.0, False, {
                "grader_name": self.grader_name,
                "threshold": self.threshold,
                "error": f"grade() raised: {exc}",
            }

        passed = score >= self.threshold
        return score, passed, {
            "grader_name": self.grader_name,
            "threshold": self.threshold,
        }
