"""Custom grader comparer — user-defined LLM evaluation prompts."""

import json
import logging

from src.comparers.base import BaseComparer
from src.providers.openai import REASONING_MODELS

logger = logging.getLogger(__name__)


class CustomGraderComparer(BaseComparer):
    """A dynamic, prompt-driven LLM grader.

    Unlike registered comparers, this class is instantiated directly by the
    eval runner using per-config grader definitions stored in ``custom_graders``.

    Each grader carries its own evaluation prompt containing ``{expected}`` and
    ``{actual}`` placeholders. Threshold-based graders must respond with a JSON
    object::

        {"score": <float 0.0-1.0>, "response": "<answer>", "reasoning": "<explanation>"}

    Informational graders with no threshold must include a free-text response::

        {"score": <float 0.0-1.0>, "response": "<answer>", "reasoning": "<explanation>"}

    Config keys (passed via ``config`` dict):
        name (str): Human-readable grader name.
        prompt (str): Evaluation prompt template with {expected}/{actual} placeholders.
        model (str): Model to use for grading. Injected by eval runner from config.
        threshold (float | None): Minimum score to pass. ``None`` makes the grader informational.
    """

    _SCORED_SYSTEM_PROMPT = (
        "You are an evaluation grader. You will be given an expected output and an actual output. "
        "Use the evaluation criteria provided by the user to score the actual output. "
        "Respond with ONLY a JSON object: "
        "{\"score\": <float 0.0-1.0>, \"response\": \"<free-text grader response>\", "
        "\"reasoning\": \"<brief explanation>\"}"
    )
    _INFORMATIONAL_SYSTEM_PROMPT = (
        "You are an evaluation grader. You will be given an expected output and an actual output. "
        "Use the evaluation criteria provided by the user to produce a free-text grading response. "
        "Respond with ONLY a JSON object: "
        "{\"score\": <float 0.0-1.0>, \"response\": \"<free-text grader response>\", "
        "\"reasoning\": \"<brief explanation>\"}"
    )

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

        # Build the user message from the template
        if "{expected}" in self.prompt_template or "{actual}" in self.prompt_template:
            user_message = self.prompt_template.format(expected=expected, actual=actual)
        else:
            # If no placeholders, append expected/actual context automatically
            user_message = (
                f"{self.prompt_template}\n\n"
                f"Expected output:\n{expected}\n\n"
                f"Actual output:\n{actual}"
            )

        request_kwargs: dict = {
            "model": self.model,
            "input": [
                {"role": "system", "content": self._system_prompt()},
                {"role": "user", "content": user_message},
            ],
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
            grader_response = result.get("response")
            if not isinstance(grader_response, str) or not grader_response.strip():
                grader_response = reasoning or text
        except (json.JSONDecodeError, ValueError):
            score = 0.0
            reasoning = f"Failed to parse grader response: {text[:200]}"
            grader_response = text

        passed = None if self.threshold is None else score >= self.threshold
        return score, passed, {
            "grader_name": self.grader_name,
            "threshold": self.threshold,
            "model": self.model,
            "response": grader_response,
            "reasoning": reasoning,
        }

    def _system_prompt(self) -> str:
        """Return the response contract for this grader mode."""
        if self.threshold is None:
            return self._INFORMATIONAL_SYSTEM_PROMPT
        return self._SCORED_SYSTEM_PROMPT
