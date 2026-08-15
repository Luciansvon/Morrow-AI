"""Antarmuka dasar BaseLLMProvider untuk penyedia model AI yang modular."""

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
    """Antarmuka abstrak penyedia model AI (OpenRouter, DeepSeek, LiteLLM)."""

    @abstractmethod
    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        model: str,
        reasoning_effort: str = "off",
        temperature: float = 0.7,
        response_format: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        """Menghasilkan respon chat completion."""
