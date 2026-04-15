"""Custom grader comparer — user-defined LLM evaluation prompts."""

import json
import logging

from src.comparers.base import BaseComparer

logger = logging.getLogger(__name__)


class CustomGraderComparer(BaseComparer):
    """A dynamic, prompt-driven LLM grader.

    Unlike registered comparers, this class is instantiated directly by the
    eval runner using per-config grader definitions stored in ``custom_graders``.

    Each grader carries its own evaluation prompt containing ``{expected}`` and
    ``{actual}`` placeholders.  The LLM must respond with a JSON object::

        {"score": <float 0.0-1.0>, "reasoning": "<explanation>"}

    Config keys (passed via ``config`` dict):
        name (str): Human-readable grader name.
        prompt (str): Evaluation prompt template with {expected}/{actual} placeholders.
        model (str): Model to use for grading. Injected by eval runner from config.
        threshold (float): Minimum score to pass. Default ``0.7``.
    """

    _SYSTEM_PROMPT = (
        "You are an evaluation grader. You will be given an expected output and an actual output. "
        "Use the evaluation criteria provided by the user to score the actual output. "
        "Respond with ONLY a JSON object: {\"score\": <float 0.0-1.0>, \"reasoning\": \"<brief explanation>\"}"
    )

    def __init__(self, config: dict | None = None) -> None:
        super().__init__(config)
        self.grader_name: str = self.config.get("name", "custom_grader")
        self.prompt_template: str = self.config.get("prompt", "")
        self.model: str = self.config.get("model", "gpt-4o-mini")  # injected by eval runner
        self.threshold: float = self.config.get("threshold", 0.7)

    async def compare(self, *, expected: str, actual: str) -> tuple[float, bool, dict]:
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

        response = await client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": self._SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.0,
        )

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

        passed = score >= self.threshold
        return score, passed, {
            "grader_name": self.grader_name,
            "threshold": self.threshold,
            "model": self.model,
            "reasoning": reasoning,
        }
