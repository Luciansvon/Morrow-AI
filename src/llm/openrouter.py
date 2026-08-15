"""OpenRouter provider dengan reasoning pass-through, usage ledger, dan fallback konservatif."""

import asyncio
import json
import time
import uuid
from typing import Any

from src.core.config import settings
from src.core.types import LLMUsageRecord
from src.llm.model_catalog import MODEL_CATALOG
from src.llm.provider import BaseLLMProvider, LLMResponse
from src.llm.usage_meter import usage_meter


def _is_transient_error(exc: Exception) -> bool:
    status = getattr(exc, "status_code", None)
    if status is None and getattr(exc, "response", None) is not None:
        status = getattr(exc.response, "status_code", None)
    if status in {408, 409, 425, 429}:
        return True
    if isinstance(status, int) and status >= 500:
        return True
    name = exc.__class__.__name__.lower()
    return any(k in name for k in ("timeout", "connection", "ratelimit", "internalserver"))


class OpenRouterProvider(BaseLLMProvider):
    def __init__(self, api_key: Any | None = None, base_url: str | None = None):
        # Simpan hanya override eksplisit. Settings dibaca saat request dijalankan agar
        # singleton global tidak membekukan nilai .env/testing saat module di-import.
        self._api_key_override = api_key
        self._base_url_override = base_url
        self._client = None

    def _effective_api_key(self) -> Any:
        return self._api_key_override if self._api_key_override is not None else settings.openrouter_api_key

    def _get_api_key_str(self) -> str:
        value = self._effective_api_key()
        return value.get_secret_value() if hasattr(value, "get_secret_value") else str(value or "")

    def _get_base_url(self) -> str:
        return self._base_url_override or settings.openrouter_base_url

    @property
    def api_key(self) -> Any:
        """Compatibility accessor; value tetap di-resolve lazily bila tidak dioverride."""
        return self._effective_api_key()

    @api_key.setter
    def api_key(self, value: Any) -> None:
        self._api_key_override = value
        self._client = None

    @property
    def base_url(self) -> str:
        return self._get_base_url()

    @base_url.setter
    def base_url(self, value: str) -> None:
        self._base_url_override = value
        self._client = None

    def _get_client(self):
        # Explicitly injected fake clients in tests are preserved. Runtime config is
        # immutable after startup, so recreating is only needed when setters are used.
        if self._client is None:
            from openai import AsyncOpenAI

            key = self._get_api_key_str().strip()
            if not key:
                raise ValueError("OPENROUTER_API_KEY belum dikonfigurasi.")
            self._client = AsyncOpenAI(
                api_key=key,
                base_url=self._get_base_url(),
                default_headers={
                    "HTTP-Referer": "https://github.com/Luciansvon/Morrow-AI",
                    "X-Title": "Morrow",
                },
            )
        return self._client

    async def _call_api(
        self,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float,
        response_format: dict[str, Any] | None,
        tools: list[dict[str, Any]] | None,
        reasoning_effort: str,
    ) -> Any:
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if response_format:
            kwargs["response_format"] = response_format
        if tools:
            kwargs["tools"] = tools
        if reasoning_effort and reasoning_effort not in {"off", "none"}:
            kwargs["extra_body"] = {
                "reasoning": {"effort": reasoning_effort, "exclude": True}
            }
        return await self._get_client().chat.completions.create(**kwargs)

    async def _call_with_retry(self, **kwargs: Any) -> Any:
        delay = 1.0
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                return await self._call_api(**kwargs)
            except Exception as exc:
                last_exc = exc
                if not _is_transient_error(exc) or attempt == 2:
                    raise
                await asyncio.sleep(delay)
                delay = min(delay * 2, 4)
        raise last_exc or RuntimeError("OpenRouter request failed")

    def _mock_content(
        self,
        messages: list[dict[str, Any]],
        response_format: dict[str, Any] | None,
    ) -> str:
        system_text = "\n".join(
            str(m.get("content", ""))
            for m in messages
            if m.get("role") == "system"
        ).lower()
        if response_format and response_format.get("type") == "json_object":
            if "hakim memori" in system_text or "memory judge" in system_text:
                return json.dumps({"should_store": False, "items": []})
            return json.dumps(
                {"owner": "manager", "confidence": 0.95, "reason": "mock routing"}
            )
        return "Halo! Saya adalah agen Morrow yang siap membantu."

    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        model: str,
        reasoning_effort: str = "off",
        temperature: float = 0.7,
        response_format: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
        usage_context: dict[str, str | None] | None = None,
    ) -> LLMResponse:
        started = time.monotonic()
        req_id = f"req_{uuid.uuid4().hex[:12]}"
        usage_context = usage_context or {}

        if self._get_api_key_str().startswith("sk-mock"):
            content = self._mock_content(messages, response_format)
            cost = usage_meter.calculate_cost(model, 100, 0, 50)
            record = LLMUsageRecord(
                request_id=req_id,
                model=model,
                input_tokens=100,
                output_tokens=50,
                cost_usd=cost,
                latency_ms=int((time.monotonic() - started) * 1000),
                group_id=usage_context.get("group_id"),
                thread_id=usage_context.get("thread_id"),
                task_id=usage_context.get("task_id"),
                role_id=usage_context.get("role_id"),
            )
            await usage_meter.record_usage(record)
            return LLMResponse(
                content=content,
                model=model,
                input_tokens=100,
                output_tokens=50,
                latency_ms=record.latency_ms,
                cost_usd=cost,
            )

        target_model = model
        call_kwargs = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "response_format": response_format,
            "tools": tools,
            "reasoning_effort": reasoning_effort,
        }
        try:
            res = await self._call_with_retry(**call_kwargs)
        except Exception as exc:
            if not _is_transient_error(exc):
                raise
            target_model = MODEL_CATALOG["gpt_5_6_luna"].model_id
            call_kwargs["model"] = target_model
            res = await self._call_with_retry(**call_kwargs)

        latency_ms = int((time.monotonic() - started) * 1000)
        choice = res.choices[0]
        content = choice.message.content or ""
        usage = getattr(res, "usage", None)
        in_tok = int(getattr(usage, "prompt_tokens", 0) or 0)
        out_tok = int(getattr(usage, "completion_tokens", 0) or 0)
        cached_tok = 0
        reasoning_tok = 0
        if usage:
            prompt_details = getattr(usage, "prompt_tokens_details", None)
            completion_details = getattr(usage, "completion_tokens_details", None)
            cached_tok = int(getattr(prompt_details, "cached_tokens", 0) or 0)
            reasoning_tok = int(getattr(completion_details, "reasoning_tokens", 0) or 0)

        api_cost = getattr(usage, "cost", None) if usage else None
        cost = (
            float(api_cost)
            if api_cost is not None
            else usage_meter.calculate_cost(target_model, in_tok, cached_tok, out_tok)
        )

        tool_calls = None
        raw_tool_calls = getattr(choice.message, "tool_calls", None)
        if raw_tool_calls:
            tool_calls = []
            for tc in raw_tool_calls:
                fn = getattr(tc, "function", None)
                tool_calls.append(
                    {
                        "id": getattr(tc, "id", None),
                        "name": getattr(fn, "name", None),
                        "arguments": getattr(fn, "arguments", None),
                    }
                )

        await usage_meter.record_usage(
            LLMUsageRecord(
                request_id=req_id,
                model=target_model,
                input_tokens=in_tok,
                cached_tokens=cached_tok,
                reasoning_tokens=reasoning_tok,
                output_tokens=out_tok,
                cost_usd=cost,
                latency_ms=latency_ms,
                group_id=usage_context.get("group_id"),
                thread_id=usage_context.get("thread_id"),
                task_id=usage_context.get("task_id"),
                role_id=usage_context.get("role_id"),
            )
        )
        return LLMResponse(
            content=content,
            model=target_model,
            input_tokens=in_tok,
            cached_tokens=cached_tok,
            reasoning_tokens=reasoning_tok,
            output_tokens=out_tok,
            latency_ms=latency_ms,
            cost_usd=cost,
            tool_calls=tool_calls,
        )


openrouter_client = OpenRouterProvider()
