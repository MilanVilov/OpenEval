"""String check grader — deterministic text comparison with template variables.

Compares two template-rendered strings using one of four operations:
``equals``, ``not_equals``, ``contains``, or ``contains_ignore_case``.

Templates use Jinja-style ``{{ item.field }}`` / ``{{ sample.output_text }}``
placeholders resolved against the CSV row and LLM output.

Config keys (passed via ``config`` dict):
    name (str): Human-readable grader name.
    input_value (str): Left-hand template string.
    operation (str): One of equals | not_equals | contains | contains_ignore_case.
    reference_value (str): Right-hand template string.
    threshold (float): Minimum score to pass. Default ``0.7``.
"""

import logging

from src.comparers.base import BaseComparer
from src.comparers.template_utils import render_template

logger = logging.getLogger(__name__)

_VALID_OPERATIONS = frozenset({
    "equals",
    "not_equals",
    "contains",
    "contains_ignore_case",
})


class StringCheckGraderComparer(BaseComparer):
    """Deterministic string comparison grader with template variable support."""

    def __init__(self, config: dict | None = None) -> None:
        super().__init__(config)
        self.grader_name: str = self.config.get("name", "string_check")
        self.input_value: str = self.config.get("input_value", "")
        self.operation: str = self.config.get("operation", "equals")
        self.reference_value: str = self.config.get("reference_value", "")
        self.threshold: float = self.config.get("threshold", 0.7)

    async def compare(
        self,
        *,
        expected: str,
        actual: str,
        row_data: dict | None = None,
    ) -> tuple[float, bool, dict]:
        """Render templates and perform the configured string comparison."""
        context = {
            "item": row_data or {},
            "sample": {"output_text": actual},
        }

        resolved_input = render_template(self.input_value, context)
        resolved_reference = render_template(self.reference_value, context)

        if self.operation not in _VALID_OPERATIONS:
            return 0.0, False, {
                "grader_name": self.grader_name,
                "error": f"Unknown operation: {self.operation}",
            }

        if self.operation == "equals":
            matched = resolved_input == resolved_reference
        elif self.operation == "not_equals":
            matched = resolved_input != resolved_reference
        elif self.operation == "contains":
            matched = resolved_reference in resolved_input
        elif self.operation == "contains_ignore_case":
            matched = resolved_reference.lower() in resolved_input.lower()
        else:
            matched = False

        score = 1.0 if matched else 0.0
        passed = score >= self.threshold

        return score, passed, {
            "grader_name": self.grader_name,
            "threshold": self.threshold,
            "operation": self.operation,
            "resolved_input": resolved_input,
            "resolved_reference": resolved_reference,
        }
