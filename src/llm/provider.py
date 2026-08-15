"""Provider abstraction untuk LLM."""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class LLMResponse(BaseModel):
    content: str
    model: str
    input_tokens: int = 0
    cached_tokens: int = 0
    reasoning_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    cost_usd: float = 0.0
    tool_calls: list[dict[str, Any]] | None = None


class BaseLLMProvider(ABC):
    @abstractmethod
    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        model: str,
        reasoning_effort: str = "off",
        temperature: float = 0.7,
        response_format: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int | None = None,
        usage_context: dict[str, str | None] | None = None,
    ) -> LLMResponse:
        """Menghasilkan chat completion."""
