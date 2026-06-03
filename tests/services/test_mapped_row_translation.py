"""Tests for mapped input translation helpers."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.providers.base import LLMResponse
from src.services.mapped_row_translation import MAX_TRANSLATION_BATCH_SIZE, translate_input_column


@pytest.mark.asyncio
async def test_translate_input_column_batches_large_pages() -> None:
    """Large row sets should be split into multiple translation requests."""
    captured_inputs: list[list[str]] = []

    async def fake_generate(**kwargs: object) -> LLMResponse:
        payload = json.loads(str(kwargs["user_input"]))
        batch_inputs = [str(item) for item in payload["inputs"]]
        captured_inputs.append(batch_inputs)
        return LLMResponse(
            text=json.dumps(
                {
                    "translations": [
                        f"translated:{item}"
                        for item in batch_inputs
                    ]
                },
            ),
            latency_ms=10,
            token_usage={"input_tokens": 1, "output_tokens": 1},
        )

    provider = SimpleNamespace(generate=AsyncMock(side_effect=fake_generate))
    rows = [
        {"input": f"Question {index}", "expected_output": f"Answer {index}"}
        for index in range(MAX_TRANSLATION_BATCH_SIZE + 1)
    ]

    translated_rows = await translate_input_column(
        rows,
        target_language="English",
        provider=provider,
    )

    assert len(captured_inputs) == 2
    assert captured_inputs[0][0] == "Question 0"
    assert captured_inputs[1] == [f"Question {MAX_TRANSLATION_BATCH_SIZE}"]
    assert translated_rows[0]["input"] == "translated:Question 0"
    assert translated_rows[-1]["expected_output"] == f"Answer {MAX_TRANSLATION_BATCH_SIZE}"
