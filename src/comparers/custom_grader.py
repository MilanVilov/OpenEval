"""Custom grader comparer — user-defined LLM evaluation prompts."""

import json
import logging

from src.comparers.base import BaseComparer
from src.comparers.template_utils import has_template_placeholders, render_template
from src.providers.openai import REASONING_MODELS

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are an evaluation grader. Always answer in English, including the reasoning field."
)


class CustomGraderComparer(BaseComparer):
    """A dynamic, prompt-driven LLM grader.

    Unlike registered comparers, this class is instantiated directly by the
    eval runner using per-config grader definitions stored in ``custom_graders``.

    Each grader carries its own evaluation prompt containing ``{expected}`` and
    ``{actual}`` placeholders.  The LLM responds with a structured JSON object::

        {"score": <float 0.0-1.0>, "reasoning": "<explanation>"}

    Config keys (passed via ``config`` dict):
        name (str): Human-readable grader name.
        prompt (str): Evaluation prompt template with {expected}/{actual} placeholders.
        model (str): Model to use for grading. Injected by eval runner from config.
        threshold (float | None): Minimum score to pass. ``None`` makes the grader informational.
    """

    _RESPONSE_FORMAT = {
        "type": "json_schema",
        "name": "grader_result",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "score": {"type": "number"},
                "reasoning": {"type": "string"},
            },
            "required": ["score", "reasoning"],
            "additionalProperties": False,
        },
    }

    def __init__(self, config: dict | None = None) -> None:
        super().__init__(config)
        self.grader_name: str = self.config.get("name", "custom_grader")
        self.prompt_template: str = self.config.get("prompt", "")
        self.model: str = self.config.get("model", "gpt-4o-mini")  # injected by eval runner
        self.threshold: float | None = self.config.get("threshold", 0.7)

    async def compare(
        self,
        *,
        expected: str,
        actual: str,
        row_data: dict | None = None,
    ) -> tuple[float, bool | None, dict]:
        """Evaluate actual output against expected using the custom prompt."""
        from src.services.openai_client import get_openai_client

        client = get_openai_client()

        # Build the user message from the template.
        # First, render {{ item.* }} / {{ sample.* }} Jinja-style placeholders,
        # then handle {expected}/{actual} Python format-string placeholders.
        context = {
            "item": row_data or {},
            "sample": {"output_text": actual},
        }
        has_template_vars = has_template_placeholders(self.prompt_template)
        rendered = render_template(self.prompt_template, context)

        if "{expected}" in rendered or "{actual}" in rendered:
            user_message = rendered.format(expected=expected, actual=actual)
        elif has_template_vars:
            # User explicitly used {{ item.* }} / {{ sample.* }} — don't auto-append
            user_message = rendered
        else:
            # If no placeholders at all, append expected/actual context automatically
            user_message = (
                f"{rendered}\n\n"
                f"Expected output:\n{expected}\n\n"
                f"Actual output:\n{actual}"
            )

        request_kwargs: dict = {
            "model": self.model,
            "input": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            "text": {"format": self._RESPONSE_FORMAT},
        }
        if self.model not in REASONING_MODELS:
            request_kwargs["temperature"] = 0.0

        response = await client.responses.create(**request_kwargs)

        # Extract text from response
        text = ""
        for item in response.output:
            if item.type == "message":
                for content in item.content:
                    if content.type == "output_text":
                        text = content.text
                        break

        try:
            result = json.loads(text)
            score = float(result.get("score", 0.0))
            reasoning = result.get("reasoning", "")
        except (json.JSONDecodeError, ValueError):
            score = 0.0
            reasoning = f"Failed to parse grader response: {text[:200]}"

        passed = None if self.threshold is None else score >= self.threshold
        return score, passed, {
            "grader_name": self.grader_name,
            "threshold": self.threshold,
            "model": self.model,
            "reasoning": reasoning,
            "raw_response": text,
        }
