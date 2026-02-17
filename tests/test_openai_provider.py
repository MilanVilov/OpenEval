"""Tests for OpenAI provider — tool building and latency measurement."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from open_eval.providers.base import LLMResponse
from open_eval.providers.openai import OpenAIProvider


class TestBuildTools:
    """Verify _build_tools produces correct OpenAI Responses API tool specs."""

    def _provider(self) -> OpenAIProvider:
        """Create a provider with a dummy client."""
        with patch("open_eval.providers.openai.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(openai_api_key="test-key")
            return OpenAIProvider(client=AsyncMock())

    def test_file_search_with_vector_store(self):
        """file_search tool should include vector_store_ids when provided."""
        provider = self._provider()
        tools = provider._build_tools(
            ["file_search"],
            {"vector_store_id": "vs_abc123"},
        )
        assert tools == [{"type": "file_search", "vector_store_ids": ["vs_abc123"]}]

    def test_file_search_without_vector_store(self):
        """file_search tool without vector_store_id should omit vector_store_ids."""
        provider = self._provider()
        tools = provider._build_tools(["file_search"], {})
        assert tools == [{"type": "file_search"}]

    def test_code_interpreter(self):
        """code_interpreter tool should produce correct spec."""
        provider = self._provider()
        tools = provider._build_tools(["code_interpreter"], {})
        assert tools == [{"type": "code_interpreter"}]

    def test_multiple_tools(self):
        """Multiple tools should all be included."""
        provider = self._provider()
        tools = provider._build_tools(
            ["file_search", "code_interpreter"],
            {"vector_store_id": "vs_xyz"},
        )
        assert len(tools) == 2
        assert {"type": "file_search", "vector_store_ids": ["vs_xyz"]} in tools
        assert {"type": "code_interpreter"} in tools

    def test_empty_tools(self):
        """Empty tools list should return empty list."""
        provider = self._provider()
        tools = provider._build_tools([], {})
        assert tools == []

    def test_unknown_tool_ignored(self):
        """Unknown tool names should be silently ignored."""
        provider = self._provider()
        tools = provider._build_tools(["unknown_tool"], {})
        assert tools == []


class TestLatencyMeasurement:
    """Verify that provider measures latency around just the API call."""

    async def test_latency_measures_api_call(self):
        """latency_ms should reflect the time spent in the API call."""
        mock_client = AsyncMock()

        # Simulate a 100ms API call
        async def slow_create(**kwargs):
            import asyncio
            await asyncio.sleep(0.1)
            resp = MagicMock()
            resp.output = []
            resp.usage = MagicMock(input_tokens=5, output_tokens=10)
            resp.id = "resp_test"
            resp.model = "gpt-4.1"
            return resp

        mock_client.responses.create = slow_create

        with patch("open_eval.providers.openai.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(openai_api_key="test-key")
            provider = OpenAIProvider(client=mock_client)

        result = await provider.generate(
            system_prompt="test",
            user_input="hello",
            model="gpt-4.1",
        )

        # Should be approximately 100ms (allow 50ms tolerance)
        assert result.latency_ms >= 80, f"Latency {result.latency_ms}ms too low"
        assert result.latency_ms < 500, f"Latency {result.latency_ms}ms too high"

    async def test_reasoning_model_skips_temperature(self):
        """Reasoning models should not include temperature in the request."""
        mock_client = AsyncMock()
        captured_kwargs = {}

        async def capture_create(**kwargs):
            captured_kwargs.update(kwargs)
            resp = MagicMock()
            resp.output = []
            resp.usage = MagicMock(input_tokens=5, output_tokens=10)
            resp.id = "resp_test"
            resp.model = "o3"
            return resp

        mock_client.responses.create = capture_create

        with patch("open_eval.providers.openai.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(openai_api_key="test-key")
            provider = OpenAIProvider(client=mock_client)

        await provider.generate(
            system_prompt="test",
            user_input="hello",
            model="o3",
            temperature=0.7,
        )

        assert "temperature" not in captured_kwargs

    async def test_tools_passed_to_api(self):
        """Tools should be correctly passed through to the API call."""
        mock_client = AsyncMock()
        captured_kwargs = {}

        async def capture_create(**kwargs):
            captured_kwargs.update(kwargs)
            resp = MagicMock()
            resp.output = []
            resp.usage = MagicMock(input_tokens=5, output_tokens=10)
            resp.id = "resp_test"
            resp.model = "gpt-4.1"
            return resp

        mock_client.responses.create = capture_create

        with patch("open_eval.providers.openai.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(openai_api_key="test-key")
            provider = OpenAIProvider(client=mock_client)

        await provider.generate(
            system_prompt="test",
            user_input="hello",
            model="gpt-4.1",
            tools=["file_search"],
            tool_options={"vector_store_id": "vs_123"},
        )

        assert "tools" in captured_kwargs
        assert captured_kwargs["tools"] == [
            {"type": "file_search", "vector_store_ids": ["vs_123"]}
        ]
