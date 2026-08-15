"""Implementasi OpenRouter Client Provider dengan integrasi failover dan retry."""

import time
import uuid
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from src.core.config import settings
from src.core.types import LLMUsageRecord
from src.llm.model_catalog import MODEL_CATALOG
from src.llm.provider import BaseLLMProvider, LLMResponse
from src.llm.usage_meter import usage_meter


class OpenRouterProvider(BaseLLMProvider):
    """Penyedia koneksi resmi ke OpenRouter API."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key = api_key or settings.openrouter_api_key
        self.base_url = base_url or settings.openrouter_base_url
        self._client = None

    def _get_api_key_str(self) -> str:
        if hasattr(self.api_key, "get_secret_value"):
            return self.api_key.get_secret_value()
        return str(self.api_key)

    def _get_client(self):
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(
                api_key=self._get_api_key_str(),
                base_url=self.base_url,
                default_headers={"HTTP-Referer": "https://morrow.ai", "X-Title": "Morrow v0.2"},
            )
        return self._client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _call_api_with_retry(
        self,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float,
        response_format: dict[str, Any] | None,
        tools: list[dict[str, Any]] | None,
    ) -> Any:
        client = self._get_client()
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if response_format:
            kwargs["response_format"] = response_format
        if tools:
            kwargs["tools"] = tools

        return await client.chat.completions.create(**kwargs)

    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        model: str,
        reasoning_effort: str = "off",
        temperature: float = 0.7,
        response_format: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        start_time = time.time()
        req_id = f"req_{uuid.uuid4().hex[:8]}"

        # Jika dalam lingkungan mock/testing dengan kunci mock
        if self._get_api_key_str().startswith("sk-mock"):
            latency_ms = int((time.time() - start_time) * 1000)
            mock_content = "Halo! Saya adalah agen Morrow yang siap membantu."
            # Jika meminta format JSON
            if response_format and response_format.get("type") == "json_object":
                mock_content = '{"owner": "manager", "confidence": 0.95, "reason": "Tugas perencanaan"}'

            cost = usage_meter.calculate_cost(model, 100, 20, 50)
            await usage_meter.record_usage(
                LLMUsageRecord(
                    request_id=req_id,
                    model=model,
                    input_tokens=100,
                    cached_tokens=20,
                    output_tokens=50,
                    cost_usd=cost,
                    latency_ms=latency_ms,
                )
            )
            return LLMResponse(
                content=mock_content,
                model=model,
                input_tokens=100,
                cached_tokens=20,
                output_tokens=50,
                latency_ms=latency_ms,
                cost_usd=cost,
            )

        # Pemanggilan nyata ke OpenRouter dengan failover ke GPT-5.6 Luna jika terjadi error
        target_model = model
        try:
            res = await self._call_api_with_retry(
                model=target_model,
                messages=messages,
                temperature=temperature,
                response_format=response_format,
                tools=tools,
            )
        except Exception:
            # Provider Outage Fallback ke GPT-5.6 Luna
            target_model = MODEL_CATALOG["gpt_5_6_luna"].model_id
            print(f"⚠️ Peringatan: {model} mengalami gangguan. Mengalihkan ke Fallback {target_model}...")
            res = await self._call_api_with_retry(
                model=target_model,
                messages=messages,
                temperature=temperature,
                response_format=response_format,
                tools=tools,
            )

        latency_ms = int((time.time() - start_time) * 1000)
        choice = res.choices[0]
        content = choice.message.content or ""
        in_tok = res.usage.prompt_tokens if res.usage else 0
        out_tok = res.usage.completion_tokens if res.usage else 0

        cached_tok = 0
        if res.usage and hasattr(res.usage, "prompt_tokens_details") and res.usage.prompt_tokens_details:
            details = res.usage.prompt_tokens_details
            if isinstance(details, dict):
                cached_tok = details.get("cached_tokens", 0) or 0
            else:
                cached_tok = getattr(details, "cached_tokens", 0) or 0

        cost = usage_meter.calculate_cost(target_model, in_tok, cached_tok, out_tok)
        await usage_meter.record_usage(
            LLMUsageRecord(
                request_id=req_id,
                model=target_model,
                input_tokens=in_tok,
                cached_tokens=cached_tok,
                output_tokens=out_tok,
                cost_usd=cost,
                latency_ms=latency_ms,
            )
        )

        return LLMResponse(
            content=content,
            model=target_model,
            input_tokens=in_tok,
            cached_tokens=cached_tok,
            output_tokens=out_tok,
            latency_ms=latency_ms,
            cost_usd=cost,
        )


openrouter_client = OpenRouterProvider()
