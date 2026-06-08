"""Translate mapped page row text values with OpenAI."""

from __future__ import annotations

import json
from dataclasses import dataclass

from src.db.repositories import MappedInputTranslationRepository
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


@dataclass(frozen=True)
class RowFieldText:
    """One mapped row field that should be translated."""

    field_name: str
    row_index: int
    source_text: str


async def translate_mapped_rows(
    mapped_rows: list[dict[str, str]],
    *,
    fields: list[str],
    target_language: str,
    provider: BaseLLMProvider | None = None,
    translation_repo: MappedInputTranslationRepository | None = None,
) -> list[dict[str, str]]:
    """Translate the requested mapped fields for one page of rows."""
    normalized_fields = _normalize_fields(fields)
    rows = _normalize_rows(mapped_rows, required_fields=normalized_fields)
    language = target_language.strip()
    if not language:
        raise ValueError("Target language is required")

    row_field_texts = _build_row_field_texts(rows, normalized_fields)
    translations = await _resolve_translations(
        [row_field_text.source_text for row_field_text in row_field_texts],
        target_language=language,
        provider=provider or OpenAIProvider(),
        translation_repo=translation_repo,
    )
    return _apply_translations(rows, row_field_texts, translations)


async def translate_input_column(
    mapped_rows: list[dict[str, str]],
    *,
    target_language: str,
    provider: BaseLLMProvider | None = None,
    translation_repo: MappedInputTranslationRepository | None = None,
) -> list[dict[str, str]]:
    """Translate only the mapped ``input`` column for a page of rows."""
    return await translate_mapped_rows(
        mapped_rows,
        fields=["input"],
        target_language=target_language,
        provider=provider,
        translation_repo=translation_repo,
    )


def _normalize_fields(fields: list[str]) -> list[str]:
    """Validate the requested mapped fields and return normalized field names."""
    normalized_fields = [field.strip() for field in fields if field.strip()]
    if not normalized_fields:
        raise ValueError("Translation fields must not be empty")
    return normalized_fields


def _normalize_rows(
    mapped_rows: list[dict[str, str]],
    *,
    required_fields: list[str],
) -> list[dict[str, str]]:
    """Return rows with string values, validating each required mapped field."""
    normalized_rows: list[dict[str, str]] = []
    for row in mapped_rows:
        missing_fields = [field for field in required_fields if field not in row]
        if missing_fields:
            missing_field_list = ", ".join(sorted(missing_fields))
            raise ValueError(f"Mapped rows must include {missing_field_list}")
        normalized_rows.append(
            {
                str(key): "" if value is None else str(value)
                for key, value in row.items()
            },
        )
    return normalized_rows


def _build_row_field_texts(
    rows: list[dict[str, str]],
    fields: list[str],
) -> list[RowFieldText]:
    """Return flattened row-field inputs in row order."""
    row_field_texts: list[RowFieldText] = []
    for row_index, row in enumerate(rows):
        for field_name in fields:
            row_field_texts.append(
                RowFieldText(
                    field_name=field_name,
                    row_index=row_index,
                    source_text=row[field_name],
                ),
            )
    return row_field_texts


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


async def _resolve_translations(
    inputs: list[str],
    *,
    target_language: str,
    provider: BaseLLMProvider,
    translation_repo: MappedInputTranslationRepository | None,
) -> list[str]:
    """Resolve translations from cache first, then translate and persist misses."""
    if not inputs:
        return []

    cached_translations: dict[str, str] = {}
    if translation_repo is not None:
        cached_translations = await translation_repo.list_by_inputs(
            target_language=_normalize_target_language(target_language),
            source_inputs=inputs,
        )

    translated_by_input: dict[str, str] = dict(cached_translations)
    for input_text in inputs:
        if input_text == "":
            translated_by_input[input_text] = ""

    missing_inputs = _unique_missing_inputs(inputs, translated_by_input)
    if missing_inputs:
        requested_translations = await _request_translation_batches(
            missing_inputs,
            target_language=target_language,
            provider=provider,
        )
        fresh_translations = dict(
            zip(missing_inputs, requested_translations, strict=True),
        )
        translated_by_input.update(fresh_translations)
        if translation_repo is not None:
            await translation_repo.upsert_many(
                target_language=_normalize_target_language(target_language),
                translations_by_input=fresh_translations,
            )

    return [translated_by_input[input_text] for input_text in inputs]


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


def _unique_missing_inputs(
    inputs: list[str],
    translated_by_input: dict[str, str],
) -> list[str]:
    """Return unique inputs that still need translation in original order."""
    missing_inputs: list[str] = []
    seen_inputs: set[str] = set()
    for input_text in inputs:
        if input_text in translated_by_input or input_text in seen_inputs:
            continue
        missing_inputs.append(input_text)
        seen_inputs.add(input_text)
    return missing_inputs


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


def _normalize_target_language(target_language: str) -> str:
    """Return the canonical cache key value for a target language."""
    return target_language.strip().casefold()


def _apply_translations(
    rows: list[dict[str, str]],
    row_field_texts: list[RowFieldText],
    translations: list[str],
) -> list[dict[str, str]]:
    """Copy rows with translated values for the requested mapped fields."""
    translated_rows: list[dict[str, str]] = []
    translation_index = 0
    for row_index, row in enumerate(rows):
        translated_row = dict(row)
        while (
            translation_index < len(row_field_texts)
            and row_field_texts[translation_index].row_index == row_index
        ):
            row_field_text = row_field_texts[translation_index]
            translated_row[row_field_text.field_name] = translations[translation_index]
            translation_index += 1
        translated_rows.append(translated_row)
    if translation_index != len(translations):
        raise ValueError("Translation response did not match the requested mapped fields")
    return translated_rows
