"""OpenAI Responses and Decisions API provider."""

import json
import logging
import re
import time

from openai import AsyncOpenAI

from src.config import get_settings
from src.providers.base import BaseLLMProvider, LLMResponse
from src.schemas.decisions import DECISION_MODEL, DecisionConfig

logger = logging.getLogger(__name__)

REASONING_MODELS = {
    "gpt-6.1-sol",
    "o3",
    "o3-pro",
    "o3-mini",
    "o4-mini",
    "gpt-5.6",
    "gpt-5.6-sol",
    "gpt-5.6-terra",
    "gpt-5.6-luna",
    "gpt-5.5",
    "gpt-5.5-pro",
    "gpt-5.4",
    "gpt-5.4-pro",
    "gpt-5.4-mini",
    "gpt-5.4-nano",
    "gpt-5.3-codex",
    "gpt-5.2",
    "gpt-5.2-pro",
    "gpt-5.1",
    "gpt-5",
    "gpt-5-pro",
    "gpt-5-mini",
    "gpt-5-nano",
}


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
        flex_enabled: bool = False,
        decision_config: dict | None = None,
    ) -> LLMResponse:
        """Call the API appropriate for the selected OpenAI model."""
        if model == DECISION_MODEL:
            return await self._generate_decision(system_prompt, user_input, decision_config)
        tool_options = tool_options or {}

        # Build input messages
        input_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ]

        # Build tools list for the Responses API
        api_tools = self._build_tools(tools or [], tool_options)

        is_reasoning = model in REASONING_MODELS or reasoning_config is not None

        # Build request kwargs
        kwargs: dict = {
            "model": model,
            "input": input_messages,
        }
        if not is_reasoning:
            kwargs["temperature"] = temperature
        if max_tokens is not None:
            kwargs["max_output_tokens"] = max_tokens
        kwargs.update(_tool_parameters(api_tools, tool_options))
        if reasoning_config:
            kwargs["reasoning"] = reasoning_config
        if response_format:
            kwargs["text"] = {"format": _response_format(response_format)}
        if flex_enabled:
            kwargs["service_tier"] = "flex"

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
        output_items = _serialize_output(response.output)

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

    async def _generate_decision(
        self,
        system_prompt: str,
        user_input: str,
        decision_config: dict | None,
    ) -> LLMResponse:
        """Evaluate questions using the SDK's generic endpoint transport."""
        config = DecisionConfig.model_validate(decision_config or {})
        questions = config.model_dump(exclude_none=True)["questions"]
        for question in questions:
            if system_prompt.strip():
                question["instructions"] = f"{system_prompt}\n\n{question['instructions']}"
        request = {"model": DECISION_MODEL, "input": user_input, "questions": questions}
        start = time.perf_counter()
        # Generic SDK transport supports Decisions without requiring the newer generated resource.
        response = await self._client.post("/decisions", cast_to=dict[str, object], body=request)
        latency_ms = int((time.perf_counter() - start) * 1000)
        return LLMResponse(
            text=json.dumps({"answers": response["answers"]}, ensure_ascii=False),
            latency_ms=latency_ms,
            token_usage={
                "input_tokens": (response.get("usage") or {}).get("input_tokens", 0),
                "output_tokens": (response.get("usage") or {}).get("output_tokens", 0),
            },
            raw_request=request,
            raw_response=response,
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


def _tool_parameters(api_tools: list, tool_options: dict) -> dict:
    """Include tool selection only when tools are enabled."""
    if not api_tools:
        return {}
    parameters = {"tools": api_tools}
    tool_choice = tool_options.get("tool_choice")
    if tool_choice and tool_choice != "auto":
        parameters["tool_choice"] = tool_choice
    return parameters


def _response_format(response_format: dict) -> dict:
    """Sanitize the schema name for the Responses API."""
    result = dict(response_format)
    if "name" in result:
        result["name"] = re.sub(r"[^a-zA-Z0-9_-]", "_", result["name"])
    return result


def _serialize_output(output: list) -> list[dict]:
    """Retain full output items for request debugging."""
    items = []
    for item in output:
        try:
            items.append(item.model_dump())
        except (AttributeError, TypeError):
            items.append({"type": getattr(item, "type", "unknown")})
    return items
