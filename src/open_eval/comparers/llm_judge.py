"""LLM judge comparer — uses an LLM to evaluate output quality."""

import json

from open_eval.comparers.base import BaseComparer, register_comparer


@register_comparer("llm_judge")
class LlmJudgeComparer(BaseComparer):
    """Use an LLM to judge whether the actual output matches the expected output.

    Config options:
        threshold (float): Minimum score for a pass. Default 0.7.
        model (str): Judge model. Default "gpt-4o-mini".
    """

    _JUDGE_PROMPT = """You are evaluating an AI model's output against an expected answer.

Expected output:
{expected}

Actual output:
{actual}

Evaluate the actual output on a scale of 0.0 to 1.0 where:
- 1.0 = perfect match in meaning and content
- 0.0 = completely wrong or irrelevant

Respond with ONLY a JSON object:
{{"score": <float>, "reasoning": "<brief explanation>"}}"""

    async def compare(self, *, expected: str, actual: str) -> tuple[float, bool, dict]:
        """Use an LLM to judge the quality of the actual output."""
        from open_eval.services.openai_client import get_openai_client

        threshold = self.config.get("threshold", 0.7)
        model = self.config.get("model", "gpt-4o-mini")

        client = get_openai_client()
        prompt = self._JUDGE_PROMPT.format(expected=expected, actual=actual)

        response = await client.responses.create(
            model=model,
            input=[{"role": "user", "content": prompt}],
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
            reasoning = f"Failed to parse judge response: {text[:200]}"

        passed = score >= threshold
        return score, passed, {"threshold": threshold, "model": model, "reasoning": reasoning}
