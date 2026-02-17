"""Tests for CustomGraderComparer — user-defined LLM evaluation prompts."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from open_eval.comparers.custom_grader import CustomGraderComparer

# The get_openai_client is imported lazily inside compare(), so we patch at its source module
_PATCH_TARGET = "open_eval.services.openai_client.get_openai_client"


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
async def test_custom_grader_uses_system_prompt():
    """The system prompt should instruct the LLM to return JSON."""
    grader = CustomGraderComparer({
        "name": "sys_check",
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
    system_msg = call_args.kwargs["input"][0]["content"]
    assert "evaluation grader" in system_msg.lower()
    assert "JSON" in system_msg


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
