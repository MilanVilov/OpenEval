"""Translate mapped dataset input values with OpenAI."""

from __future__ import annotations

import json

from src.providers.base import BaseLLMProvider
from src.providers.openai import OpenAIProvider

MAX_TRANSLATION_BATCH_SIZE = 50
TRANSLATION_MODEL = "gpt-5.4-nano"
TRANSLATION_RESPONSE_FORMAT = {
    "type": "json_schema",
    "name": "translated_inputs",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "translations": {
                "type": "array",
                "items": {"type": "string"},
            }
        },
        "required": ["translations"],
        "additionalProperties": False,
    },
}
TRANSLATION_SYSTEM_PROMPT = """
Translate each input string into the requested language.
Preserve row order, line breaks, markdown, URLs, code blocks, placeholders, and empty strings.
Return only JSON that matches the schema.
""".strip()


async def translate_input_column(
    mapped_rows: list[dict[str, str]],
    *,
    target_language: str,
    provider: BaseLLMProvider | None = None,
) -> list[dict[str, str]]:
    """Translate only the mapped ``input`` column for a page of rows."""
    rows = _normalize_rows(mapped_rows)
    language = target_language.strip()
    if not language:
        raise ValueError("Target language is required")

    translations = await _request_translation_batches(
        [row["input"] for row in rows],
        target_language=language,
        provider=provider or OpenAIProvider(),
    )
    return _apply_translations(rows, translations)


def _normalize_rows(mapped_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Return rows with string values, validating the mapped input column."""
    normalized_rows: list[dict[str, str]] = []
    for row in mapped_rows:
        if "input" not in row:
            raise ValueError("Mapped rows must include input")
        normalized_rows.append(
            {
                str(key): "" if value is None else str(value)
                for key, value in row.items()
            },
        )
    return normalized_rows


async def _request_translations(
    inputs: list[str],
    *,
    target_language: str,
    provider: BaseLLMProvider,
) -> list[str]:
    """Request translated input strings from OpenAI."""
    response = await provider.generate(
        system_prompt=TRANSLATION_SYSTEM_PROMPT,
        user_input=json.dumps(
            {"target_language": target_language, "inputs": inputs},
            ensure_ascii=False,
        ),
        model=TRANSLATION_MODEL,
        reasoning_config={"effort": "none"},
        response_format=TRANSLATION_RESPONSE_FORMAT,
    )
    return _parse_translations(response.text, expected_count=len(inputs))


async def _request_translation_batches(
    inputs: list[str],
    *,
    target_language: str,
    provider: BaseLLMProvider,
) -> list[str]:
    """Translate inputs in fixed-size batches to keep prompts bounded."""
    translations: list[str] = []
    for batch in _batch_inputs(inputs):
        translations.extend(
            await _request_translation_batch_with_fallback(
                batch,
                target_language=target_language,
                provider=provider,
            ),
        )
    return translations


def _batch_inputs(inputs: list[str]) -> list[list[str]]:
    """Split inputs into bounded batches for the translation model."""
    return [
        inputs[index : index + MAX_TRANSLATION_BATCH_SIZE]
        for index in range(0, len(inputs), MAX_TRANSLATION_BATCH_SIZE)
    ]


async def _request_translation_batch_with_fallback(
    inputs: list[str],
    *,
    target_language: str,
    provider: BaseLLMProvider,
) -> list[str]:
    """Translate one batch, falling back to single-row requests on format mismatch."""
    try:
        return await _request_translations(
            inputs,
            target_language=target_language,
            provider=provider,
        )
    except ValueError:
        if len(inputs) == 1:
            raise
        return await _request_single_row_translations(
            inputs,
            target_language=target_language,
            provider=provider,
        )


async def _request_single_row_translations(
    inputs: list[str],
    *,
    target_language: str,
    provider: BaseLLMProvider,
) -> list[str]:
    """Translate rows one at a time as a resilient fallback path."""
    translations: list[str] = []
    for input_text in inputs:
        translations.extend(
            await _request_translations(
                [input_text],
                target_language=target_language,
                provider=provider,
            ),
        )
    return translations


def _parse_translations(response_text: str, *, expected_count: int) -> list[str]:
    """Validate the model response and return translated strings."""
    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise ValueError("Translation response was not valid JSON") from exc

    translations = payload.get("translations")
    if not isinstance(translations, list):
        raise ValueError("Translation response is missing translations")
    if len(translations) != expected_count:
        raise ValueError("Translation response did not match the page row count")
    if any(not isinstance(item, str) for item in translations):
        raise ValueError("Translation response must contain strings only")
    return translations


def _apply_translations(
    rows: list[dict[str, str]],
    translations: list[str],
) -> list[dict[str, str]]:
    """Copy rows with translated ``input`` values."""
    translated_rows: list[dict[str, str]] = []
    for row, translation in zip(rows, translations, strict=True):
        translated_row = dict(row)
        translated_row["input"] = translation
        translated_rows.append(translated_row)
    return translated_rows
