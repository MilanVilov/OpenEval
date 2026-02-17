"""Evaluation client service — thin wrapper around LLM providers."""

from open_eval.providers.base import LLMResponse
from open_eval.providers.openai import OpenAIProvider


async def call_llm(
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
    """Call the LLM provider with the given parameters.

    Currently uses OpenAI. Could be extended to support other providers.
    """
    provider = OpenAIProvider()
    return await provider.generate(
        system_prompt=system_prompt,
        user_input=user_input,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        tools=tools,
        tool_options=tool_options,
        reasoning_config=reasoning_config,
        response_format=response_format,
    )
