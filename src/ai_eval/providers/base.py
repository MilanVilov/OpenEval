"""Base LLM provider interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""

    text: str
    latency_ms: int
    token_usage: dict  # {"input_tokens": int, "output_tokens": int}
    raw_response: dict | None = None


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
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
        """Send a prompt to the LLM and return a standardized response.

        Args:
            system_prompt: System instructions for the model.
            user_input: The user's input text.
            model: Model identifier (e.g. "gpt-4o").
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in the response.
            tools: List of tool names to enable (e.g. ["file_search", "code_interpreter"]).
            tool_options: Additional tool config (e.g. {"vector_store_id": "vs_xxx"}).
            reasoning_config: Reasoning configuration (e.g. {"effort": "medium"}).
            response_format: Response format configuration (e.g. {"type": "json_object"}).

        Returns:
            LLMResponse with generated text and metadata.
        """
        ...
