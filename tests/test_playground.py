"""Tests for Playground configuration execution."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.providers.base import LLMResponse
from src.routers.playground import run_playground
from src.routers.schemas.playground import PlaygroundRequest


@pytest.mark.asyncio
async def test_playground_uses_standard_processing():
    """Playground should not inherit a Flex setting from the configuration."""
    config = MagicMock(
        system_prompt="You are helpful.",
        model="gpt-4.1",
        temperature=0.7,
        max_tokens=None,
        tools=[],
        tool_options={},
        reasoning_config=None,
        response_format=None,
    )
    provider = MagicMock()
    provider.generate = AsyncMock(
        return_value=LLMResponse(
            text="Hi",
            latency_ms=10,
            token_usage={"input_tokens": 1, "output_tokens": 1},
            raw_request={},
            raw_response={},
        )
    )

    with (
        patch("src.routers.playground.ConfigRepository") as repository,
        patch("src.routers.playground.OpenAIProvider", return_value=provider),
    ):
        repository.return_value.get_by_id = AsyncMock(return_value=config)
        await run_playground(PlaygroundRequest(config_id="config", message="Hello"), AsyncMock())

    assert "flex_enabled" not in provider.generate.await_args.kwargs
