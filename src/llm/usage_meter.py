"""Usage ledger, fallback estimator, dan thread budget guard."""

import uuid

from src.core.config import settings
from src.core.types import LLMUsageRecord
from src.llm.model_catalog import MODEL_CATALOG
from src.storage.sqlite import db


class UsageMeter:
    @staticmethod
    def calculate_cost(model_id: str, input_tokens: int, cached_tokens: int, output_tokens: int) -> float:
        spec = next((s for s in MODEL_CATALOG.values() if s.model_id == model_id), None)
        if not spec:
            return 0.0
        input_rate = spec.input_price_1m / 1_000_000
        output_rate = spec.output_price_1m / 1_000_000
        cached_rate = (
            spec.cached_input_price_1m / 1_000_000
            if spec.cached_input_price_1m is not None
            else input_rate
        )
        non_cached = max(0, input_tokens - cached_tokens)
        return round(non_cached * input_rate + cached_tokens * cached_rate + output_tokens * output_rate, 8)

    @classmethod
    async def record_usage(cls, record: LLMUsageRecord) -> None:
        await db.execute(
            """INSERT INTO usage_ledger
               (id, request_id, task_id, role_id, group_id, thread_id, model, provider,
                input_tokens, cached_tokens, reasoning_tokens, output_tokens, cost_usd, latency_ms)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                uuid.uuid4().hex[:16], record.request_id, record.task_id, record.role_id,
                record.group_id, record.thread_id, record.model, record.provider,
                record.input_tokens, record.cached_tokens, record.reasoning_tokens,
                record.output_tokens, record.cost_usd, record.latency_ms,
            ),
        )

    @classmethod
    async def spent_for_thread(cls, group_id: str, thread_id: str | None = None) -> float:
        if thread_id:
            row = await db.fetch_one(
                "SELECT COALESCE(SUM(cost_usd),0) AS total FROM usage_ledger WHERE group_id=? AND thread_id=?",
                (group_id, thread_id),
            )
        else:
            row = await db.fetch_one(
                "SELECT COALESCE(SUM(cost_usd),0) AS total FROM usage_ledger WHERE group_id=?",
                (group_id,),
            )
        return float(row["total"] if row else 0.0)

    @classmethod
    async def check_thread_budget(
        cls,
        group_id: str,
        thread_id: str | None = None,
        limit: float | None = None,
    ) -> bool:
        budget = settings.budget_thread_total if limit is None else limit
        return await cls.spent_for_thread(group_id, thread_id) < budget


usage_meter = UsageMeter()
