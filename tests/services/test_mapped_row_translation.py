"""Tests for mapped input translation helpers."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.providers.base import LLMResponse
from src.services.mapped_row_translation import MAX_TRANSLATION_BATCH_SIZE, translate_mapped_rows


@pytest.mark.asyncio
async def test_translate_mapped_rows_batches_large_pages() -> None:
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

    translated_rows = await translate_mapped_rows(
        rows,
        fields=["input"],
        target_language="English",
        provider=provider,
    )

    assert len(captured_inputs) == 2
    assert captured_inputs[0][0] == "Question 0"
    assert captured_inputs[1] == [f"Question {MAX_TRANSLATION_BATCH_SIZE}"]
    assert translated_rows[0]["input"] == "translated:Question 0"
    assert translated_rows[-1]["expected_output"] == f"Answer {MAX_TRANSLATION_BATCH_SIZE}"


@pytest.mark.asyncio
async def test_translate_mapped_rows_falls_back_to_single_rows_on_count_mismatch() -> None:
    """A malformed batch response should retry each row individually."""
    captured_inputs: list[list[str]] = []

    async def fake_generate(**kwargs: object) -> LLMResponse:
        payload = json.loads(str(kwargs["user_input"]))
        batch_inputs = [str(item) for item in payload["inputs"]]
        captured_inputs.append(batch_inputs)

        if len(batch_inputs) > 1:
            translations = [f"translated:{batch_inputs[0]}"]
        else:
            translations = [f"translated:{batch_inputs[0]}"]

        return LLMResponse(
            text=json.dumps({"translations": translations}),
            latency_ms=10,
            token_usage={"input_tokens": 1, "output_tokens": 1},
        )

    provider = SimpleNamespace(generate=AsyncMock(side_effect=fake_generate))
    rows = [
        {"input": "Question 1", "expected_output": "Answer 1"},
        {"input": "Question 2", "expected_output": "Answer 2"},
    ]

    translated_rows = await translate_mapped_rows(
        rows,
        fields=["input"],
        target_language="English",
        provider=provider,
    )

    assert captured_inputs == [["Question 1", "Question 2"], ["Question 1"], ["Question 2"]]
    assert [row["input"] for row in translated_rows] == [
        "translated:Question 1",
        "translated:Question 2",
    ]


@pytest.mark.asyncio
async def test_translate_mapped_rows_reuses_cached_translations() -> None:
    """Cached translations should bypass the model call across all requested fields."""
    provider = SimpleNamespace(generate=AsyncMock())
    translation_repo = SimpleNamespace(
        list_by_inputs=AsyncMock(
            return_value={"Question 1": "Vraag 1", "Answer 1": "Antwoord 1"},
        ),
        upsert_many=AsyncMock(),
    )

    translated_rows = await translate_mapped_rows(
        [{"input": "Question 1", "expected_output": "Answer 1"}],
        fields=["input", "expected_output"],
        target_language="Dutch",
        provider=provider,
        translation_repo=translation_repo,
    )

    assert translated_rows == [{"input": "Vraag 1", "expected_output": "Antwoord 1"}]
    provider.generate.assert_not_awaited()
    translation_repo.list_by_inputs.assert_awaited_once_with(
        target_language="dutch",
        source_inputs=["Question 1", "Answer 1"],
    )
    translation_repo.upsert_many.assert_not_awaited()


@pytest.mark.asyncio
async def test_translate_mapped_rows_persists_new_translations() -> None:
    """Fresh translations should be cached after the model returns them."""
    provider = SimpleNamespace(
        generate=AsyncMock(
            return_value=LLMResponse(
                text='{"translations":["Vraag 1","Antwoord 1","Vraag 2","Antwoord 2"]}',
                latency_ms=10,
                token_usage={"input_tokens": 1, "output_tokens": 1},
            ),
        ),
    )
    translation_repo = SimpleNamespace(
        list_by_inputs=AsyncMock(return_value={}),
        upsert_many=AsyncMock(),
    )

    translated_rows = await translate_mapped_rows(
        [
            {"input": "Question 1", "expected_output": "Answer 1"},
            {"input": "Question 2", "expected_output": "Answer 2"},
        ],
        fields=["input", "expected_output"],
        target_language="Dutch",
        provider=provider,
        translation_repo=translation_repo,
    )

    assert [row["input"] for row in translated_rows] == ["Vraag 1", "Vraag 2"]
    assert [row["expected_output"] for row in translated_rows] == [
        "Antwoord 1",
        "Antwoord 2",
    ]
    translation_repo.upsert_many.assert_awaited_once_with(
        target_language="dutch",
        translations_by_input={
            "Question 1": "Vraag 1",
            "Answer 1": "Antwoord 1",
            "Question 2": "Vraag 2",
            "Answer 2": "Antwoord 2",
        },
    )


@pytest.mark.asyncio
async def test_translate_mapped_rows_deduplicates_repeated_text_across_fields() -> None:
    """Repeated text should be translated once even when multiple fields use it."""
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

    translated_rows = await translate_mapped_rows(
        [
            {
                "input": "Shared text",
                "expected_output": "Shared text",
                "actual_output": "Unique text",
            }
        ],
        fields=["input", "expected_output", "actual_output"],
        target_language="Dutch",
        provider=provider,
    )

    assert captured_inputs == [["Shared text", "Unique text"]]
    assert translated_rows == [
        {
            "input": "translated:Shared text",
            "expected_output": "translated:Shared text",
            "actual_output": "translated:Unique text",
        }
    ]
