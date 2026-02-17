"""OpenAI Responses API provider."""

import logging
import time

from openai import AsyncOpenAI

from open_eval.config import get_settings
from open_eval.providers.base import BaseLLMProvider, LLMResponse

logger = logging.getLogger(__name__)


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
        reasoning_config: dict | None = None,
        response_format: dict | None = None,
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

        # Models that use reasoning and don't support temperature
        _reasoning_models = {
            "o3", "o3-pro", "o3-mini", "o4-mini",
            "gpt-5.4", "gpt-5.4-mini", "gpt-5.4-nano",
            "gpt-5.2", "gpt-5.2-pro", "gpt-5.1",
            "gpt-5", "gpt-5-mini", "gpt-5-nano",
        }
        is_reasoning = model in _reasoning_models or reasoning_config is not None

        # Build request kwargs
        kwargs: dict = {
            "model": model,
            "input": input_messages,
        }
        if not is_reasoning:
            kwargs["temperature"] = temperature
        if max_tokens is not None:
            kwargs["max_output_tokens"] = max_tokens
        if api_tools:
            kwargs["tools"] = api_tools
            # tool_choice: "auto" (default), "required", or "none"
            tool_choice = tool_options.get("tool_choice")
            if tool_choice and tool_choice != "auto":
                kwargs["tool_choice"] = tool_choice
        if reasoning_config:
            kwargs["reasoning"] = reasoning_config
        if response_format:
            fmt = dict(response_format)
            # OpenAI requires name to match ^[a-zA-Z0-9_-]+$
            if "name" in fmt:
                import re
                fmt["name"] = re.sub(r"[^a-zA-Z0-9_-]", "_", fmt["name"])
            kwargs["text"] = {"format": fmt}

        # Log the request for debugging (tools, model, etc.)
        logger.info(
            "OpenAI request: model=%s tools=%s reasoning=%s text_format=%s",
            kwargs.get("model"),
            kwargs.get("tools"),
            kwargs.get("reasoning"),
            kwargs.get("text"),
        )

        # Snapshot request kwargs for debugging
        raw_request = {k: v for k, v in kwargs.items()}

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

        # Serialize output items for full response visibility
        output_items = []
        for item in response.output:
            try:
                output_items.append(item.model_dump())
            except Exception:
                output_items.append({"type": getattr(item, "type", "unknown")})

        return LLMResponse(
            text=text,
            latency_ms=latency_ms,
            token_usage=token_usage,
            raw_response={
                "id": response.id,
                "model": response.model,
                "output": output_items,
            },
            raw_request=raw_request,
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
            elif tool_name == "shell":
                shell_spec: dict = {"type": "shell"}
                container_id = tool_options.get("container_id")
                if container_id:
                    shell_spec["environment"] = {
                        "type": "container_reference",
                        "container_id": container_id,
                    }
                else:
                    shell_spec["environment"] = {"type": "container_auto"}
                api_tools.append(shell_spec)
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
