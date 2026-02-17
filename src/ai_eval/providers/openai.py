"""OpenAI Responses API provider."""

import time

from openai import AsyncOpenAI

from ai_eval.config import get_settings
from ai_eval.providers.base import BaseLLMProvider, LLMResponse


class OpenAIProvider(BaseLLMProvider):
    """LLM provider using OpenAI's Responses API."""

    def __init__(self, client: AsyncOpenAI | None = None) -> None:
        self._client = client or AsyncOpenAI(api_key=get_settings().openai_api_key)

    async def generate(
        self,
        *,
        system_prompt: str,
        user_input: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        tools: list | None = None,
        tool_options: dict | None = None,
    ) -> LLMResponse:
        """Call the OpenAI Responses API."""
        tool_options = tool_options or {}

        # Build input messages
        input_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ]

        # Build tools list for the Responses API
        api_tools = self._build_tools(tools or [], tool_options)

        # Build request kwargs
        kwargs: dict = {
            "model": model,
            "input": input_messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            kwargs["max_output_tokens"] = max_tokens
        if api_tools:
            kwargs["tools"] = api_tools

        start = time.perf_counter()
        response = await self._client.responses.create(**kwargs)
        latency_ms = int((time.perf_counter() - start) * 1000)

        # Extract text from response output items
        text = self._extract_text(response)

        # Extract token usage
        token_usage = {
            "input_tokens": response.usage.input_tokens if response.usage else 0,
            "output_tokens": response.usage.output_tokens if response.usage else 0,
        }

        return LLMResponse(
            text=text,
            latency_ms=latency_ms,
            token_usage=token_usage,
            raw_response={"id": response.id, "model": response.model},
        )

    def _build_tools(self, tools: list, tool_options: dict) -> list:
        """Convert tool names to OpenAI Responses API tool specs."""
        api_tools = []
        for tool_name in tools:
            if tool_name == "file_search":
                tool_spec: dict = {"type": "file_search"}
                vector_store_id = tool_options.get("vector_store_id")
                if vector_store_id:
                    tool_spec["vector_store_ids"] = [vector_store_id]
                api_tools.append(tool_spec)
            elif tool_name == "code_interpreter":
                api_tools.append({"type": "code_interpreter"})
        return api_tools

    def _extract_text(self, response: object) -> str:
        """Extract the text content from a Responses API response."""
        parts = []
        for item in response.output:
            if item.type == "message":
                for content in item.content:
                    if content.type == "output_text":
                        parts.append(content.text)
        return "\n".join(parts) if parts else ""
