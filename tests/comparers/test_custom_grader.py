"""Tests for CustomGraderComparer — user-defined LLM evaluation prompts."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.comparers.custom_grader import CustomGraderComparer

# The get_openai_client is imported lazily inside compare(), so we patch at its source module
_PATCH_TARGET = "src.services.openai_client.get_openai_client"


def _make_openai_response(score: float, reasoning: str) -> MagicMock:
    """Create a mock OpenAI response with a JSON score payload."""
    text_content = MagicMock()
    text_content.type = "output_text"
    text_content.text = json.dumps({"score": score, "reasoning": reasoning})

    message = MagicMock()
    message.type = "message"
    message.content = [text_content]

    response = MagicMock()
    response.output = [message]
    return response


def _make_openai_response_bad_json() -> MagicMock:
    """Create a mock OpenAI response with unparseable text."""
    text_content = MagicMock()
    text_content.type = "output_text"
    text_content.text = "This is not JSON"

    message = MagicMock()
    message.type = "message"
    message.content = [text_content]

    response = MagicMock()
    response.output = [message]
    return response


@pytest.mark.asyncio
async def test_custom_grader_passes_above_threshold():
    """A score above the threshold should pass."""
    grader = CustomGraderComparer({
        "name": "tone_check",
        "prompt": "Check if the tone matches.\n\nExpected: {expected}\nActual: {actual}",
        "model": "gpt-4o-mini",
        "threshold": 0.7,
    })

    mock_client = AsyncMock()
    mock_client.responses.create = AsyncMock(
        return_value=_make_openai_response(0.9, "Great tone match"),
    )

    with patch(_PATCH_TARGET, return_value=mock_client):
        score, passed, details = await grader.compare(
            expected="Hello there",
            actual="Hi there!",
        )

    assert score == 0.9
    assert passed is True
    assert details["grader_name"] == "tone_check"
    assert details["reasoning"] == "Great tone match"
    assert details["threshold"] == 0.7
    assert details["model"] == "gpt-4o-mini"
    assert details["raw_response"] == '{"score": 0.9, "reasoning": "Great tone match"}'

    # Verify prompt template was interpolated correctly
    call_args = mock_client.responses.create.call_args
    user_msg = call_args.kwargs["input"][1]["content"]
    assert "Hello there" in user_msg
    assert "Hi there!" in user_msg


@pytest.mark.asyncio
async def test_custom_grader_fails_below_threshold():
    """A score below the threshold should fail."""
    grader = CustomGraderComparer({
        "name": "accuracy",
        "prompt": "Expected: {expected}\nActual: {actual}\nRate accuracy.",
        "model": "gpt-4o-mini",
        "threshold": 0.8,
    })

    mock_client = AsyncMock()
    mock_client.responses.create = AsyncMock(
        return_value=_make_openai_response(0.5, "Partially correct"),
    )

    with patch(_PATCH_TARGET, return_value=mock_client):
        score, passed, details = await grader.compare(
            expected="Paris",
            actual="London",
        )

    assert score == 0.5
    assert passed is False
    assert details["reasoning"] == "Partially correct"


@pytest.mark.asyncio
async def test_custom_grader_null_threshold_returns_score_only():
    """A null threshold should keep the LLM score but omit pass/fail judgment."""
    grader = CustomGraderComparer({
        "name": "score_only",
        "prompt": "Expected: {expected}\nActual: {actual}",
        "model": "gpt-4o-mini",
        "threshold": None,
    })

    mock_client = AsyncMock()
    mock_client.responses.create = AsyncMock(
        return_value=_make_openai_response(0.2, "Weak match"),
    )

    with patch(_PATCH_TARGET, return_value=mock_client):
        score, passed, details = await grader.compare(
            expected="Paris",
            actual="London",
        )

    assert score == 0.2
    assert passed is None
    assert details["threshold"] is None


@pytest.mark.asyncio
async def test_custom_grader_handles_bad_json():
    """Unparseable LLM response should yield score 0.0 and fail."""
    grader = CustomGraderComparer({
        "name": "broken",
        "prompt": "Evaluate: {expected} vs {actual}",
        "model": "gpt-4o-mini",
        "threshold": 0.5,
    })

    mock_client = AsyncMock()
    mock_client.responses.create = AsyncMock(
        return_value=_make_openai_response_bad_json(),
    )

    with patch(_PATCH_TARGET, return_value=mock_client):
        score, passed, details = await grader.compare(
            expected="expected",
            actual="actual",
        )

    assert score == 0.0
    assert passed is False
    assert "Failed to parse" in details["reasoning"]


@pytest.mark.asyncio
async def test_custom_grader_auto_appends_context_when_no_placeholders():
    """If prompt has no {expected}/{actual}, context is appended automatically."""
    grader = CustomGraderComparer({
        "name": "simple_check",
        "prompt": "Rate the quality of the response.",
        "model": "gpt-4o-mini",
        "threshold": 0.5,
    })

    mock_client = AsyncMock()
    mock_client.responses.create = AsyncMock(
        return_value=_make_openai_response(0.8, "Good quality"),
    )

    with patch(_PATCH_TARGET, return_value=mock_client):
        await grader.compare(expected="foo", actual="bar")

    call_args = mock_client.responses.create.call_args
    user_msg = call_args.kwargs["input"][1]["content"]
    assert "Rate the quality of the response." in user_msg
    assert "Expected output:\nfoo" in user_msg
    assert "Actual output:\nbar" in user_msg


@pytest.mark.asyncio
async def test_custom_grader_uses_english_system_prompt_and_json_schema_response_format():
    """Grader requests English reasoning through a system prompt and structured output."""
    grader = CustomGraderComparer({
        "name": "schema_check",
        "prompt": "Check: {expected} vs {actual}",
        "model": "gpt-4o-mini",
        "threshold": 0.5,
    })

    mock_client = AsyncMock()
    mock_client.responses.create = AsyncMock(
        return_value=_make_openai_response(1.0, "Perfect"),
    )

    with patch(_PATCH_TARGET, return_value=mock_client):
        await grader.compare(expected="a", actual="a")

    call_args = mock_client.responses.create.call_args
    messages = call_args.kwargs["input"]
    assert messages[0] == {
        "role": "system",
        "content": (
            "You are an evaluation grader. Always answer in English, "
            "including the reasoning field."
        ),
    }
    assert messages[1]["role"] == "user"
    # No JSON format instruction in the user message itself
    assert "Respond with ONLY" not in messages[1]["content"]
    # JSON schema enforced via text.format
    text_format = call_args.kwargs["text"]["format"]
    assert text_format["type"] == "json_schema"
    assert text_format["strict"] is True
    assert "score" in text_format["schema"]["properties"]
    assert "reasoning" in text_format["schema"]["properties"]


@pytest.mark.asyncio
async def test_custom_grader_default_values():
    """Defaults should be applied when config keys are missing.

    In production the eval runner injects config.model, so the model
    key is always present. This tests the fallback default.
    """
    grader = CustomGraderComparer({})

    assert grader.grader_name == "custom_grader"
    assert grader.prompt_template == ""
    assert grader.model == "gpt-4o-mini"
    assert grader.threshold == 0.7


@pytest.mark.asyncio
async def test_custom_grader_uses_injected_model():
    """The eval runner injects config.model into the grader config dict."""
    grader = CustomGraderComparer({
        "name": "injected_model",
        "prompt": "Check: {expected} vs {actual}",
        "model": "gpt-4.1",
        "threshold": 0.5,
    })

    assert grader.model == "gpt-4.1"

    mock_client = AsyncMock()
    mock_client.responses.create = AsyncMock(
        return_value=_make_openai_response(0.9, "Fine"),
    )

    with patch(_PATCH_TARGET, return_value=mock_client):
        await grader.compare(expected="a", actual="b")

    call_args = mock_client.responses.create.call_args
    assert call_args.kwargs["model"] == "gpt-4.1"


@pytest.mark.asyncio
async def test_custom_grader_omits_temperature_for_reasoning_model():
    """Reasoning prompt graders should not send unsupported temperature."""
    grader = CustomGraderComparer({
        "name": "reasoning_grader",
        "prompt": "Check: {expected} vs {actual}",
        "model": "gpt-5.5",
        "threshold": 0.5,
    })

    mock_client = AsyncMock()
    mock_client.responses.create = AsyncMock(
        return_value=_make_openai_response(0.9, "Fine"),
    )

    with patch(_PATCH_TARGET, return_value=mock_client):
        await grader.compare(expected="a", actual="b")

    call_args = mock_client.responses.create.call_args
    assert call_args.kwargs["model"] == "gpt-5.5"
    assert "temperature" not in call_args.kwargs


@pytest.mark.asyncio
async def test_custom_grader_sends_temperature_for_non_reasoning_model():
    """Non-reasoning prompt graders should keep deterministic temperature."""
    grader = CustomGraderComparer({
        "name": "standard_grader",
        "prompt": "Check: {expected} vs {actual}",
        "model": "gpt-4o-mini",
        "threshold": 0.5,
    })

    mock_client = AsyncMock()
    mock_client.responses.create = AsyncMock(
        return_value=_make_openai_response(0.9, "Fine"),
    )

    with patch(_PATCH_TARGET, return_value=mock_client):
        await grader.compare(expected="a", actual="b")

    call_args = mock_client.responses.create.call_args
    assert call_args.kwargs["temperature"] == 0.0


@pytest.mark.asyncio
async def test_custom_grader_renders_item_template_variables():
    """Template variables like {{ item.input }} should be resolved from row_data."""
    grader = CustomGraderComparer({
        "name": "context_grader",
        "prompt": (
            "The user asked: {{ item.input }}\n"
            "Expected: {expected}\n"
            "Actual: {actual}\n"
            "Category: {{ item.category }}"
        ),
        "model": "gpt-4o-mini",
        "threshold": 0.7,
    })

    mock_client = AsyncMock()
    mock_client.responses.create = AsyncMock(
        return_value=_make_openai_response(0.85, "Correct with context"),
    )

    with patch(_PATCH_TARGET, return_value=mock_client):
        score, passed, details = await grader.compare(
            expected="Paris",
            actual="Paris",
            row_data={"input": "What is the capital of France?", "category": "geography"},
        )

    assert score == 0.85
    assert passed is True

    call_args = mock_client.responses.create.call_args
    user_msg = call_args.kwargs["input"][1]["content"]
    assert "What is the capital of France?" in user_msg
    assert "geography" in user_msg
    assert "Paris" in user_msg


@pytest.mark.asyncio
async def test_custom_grader_renders_sample_output_text():
    """{{ sample.output_text }} should resolve to the actual LLM output."""
    grader = CustomGraderComparer({
        "name": "sample_grader",
        "prompt": "LLM said: {{ sample.output_text }}\nExpected: {expected}",
        "model": "gpt-4o-mini",
        "threshold": 0.5,
    })

    mock_client = AsyncMock()
    mock_client.responses.create = AsyncMock(
        return_value=_make_openai_response(0.7, "Matched"),
    )

    with patch(_PATCH_TARGET, return_value=mock_client):
        await grader.compare(expected="42", actual="The answer is 42")

    call_args = mock_client.responses.create.call_args
    user_msg = call_args.kwargs["input"][1]["content"]
    assert "The answer is 42" in user_msg
    assert "42" in user_msg


@pytest.mark.asyncio
async def test_custom_grader_unresolved_template_left_as_is():
    """Unresolvable {{ item.missing }} placeholders should remain in the prompt."""
    grader = CustomGraderComparer({
        "name": "missing_field",
        "prompt": "Field: {{ item.nonexistent }}\nExpected: {expected}\nActual: {actual}",
        "model": "gpt-4o-mini",
        "threshold": 0.5,
    })

    mock_client = AsyncMock()
    mock_client.responses.create = AsyncMock(
        return_value=_make_openai_response(0.5, "ok"),
    )

    with patch(_PATCH_TARGET, return_value=mock_client):
        await grader.compare(expected="a", actual="b", row_data={"input": "hello"})

    call_args = mock_client.responses.create.call_args
    user_msg = call_args.kwargs["input"][1]["content"]
    assert "{ item.nonexistent }" in user_msg


@pytest.mark.asyncio
async def test_custom_grader_template_vars_without_expected_actual_no_auto_append():
    """When using {{ item.* }} without {expected}/{actual}, don't auto-append expected/actual."""
    grader = CustomGraderComparer({
        "name": "standalone_template",
        "prompt": "Check if the text in: {{ item.input }} is longer than 100 chars.",
        "model": "gpt-4o-mini",
        "threshold": 0.7,
    })

    mock_client = AsyncMock()
    mock_client.responses.create = AsyncMock(
        return_value=_make_openai_response(0.9, "Long enough"),
    )

    with patch(_PATCH_TARGET, return_value=mock_client):
        await grader.compare(
            expected="some expected",
            actual="some actual",
            row_data={"input": "A very long input text that should be evaluated"},
        )

    call_args = mock_client.responses.create.call_args
    user_msg = call_args.kwargs["input"][1]["content"]
    # Template variable should be resolved
    assert "A very long input text that should be evaluated" in user_msg
    # Expected/actual should NOT be auto-appended
    assert "Expected output:" not in user_msg
    assert "Actual output:" not in user_msg
    assert "some expected" not in user_msg
