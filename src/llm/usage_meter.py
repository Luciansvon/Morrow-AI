"""Pencatat penggunaan token, kalkulator biaya, dan penjaga anggaran (Budget Guard)."""

import uuid

from src.core.config import settings
from src.core.types import LLMUsageRecord
from src.llm.model_catalog import MODEL_CATALOG
from src.storage.sqlite import db


class UsageMeter:
    """Manajer pencatatan biaya dan pembatas anggaran."""

    @staticmethod
    def calculate_cost(
        model_id: str,
        input_tokens: int,
        cached_tokens: int,
        output_tokens: int,
    ) -> float:
        """Menghitung estimasi biaya dalam USD dengan diskon prompt caching 80%."""
        spec = None
        for s in MODEL_CATALOG.values():
            if s.model_id == model_id:
                spec = s
                break

        if not spec:
            # Default rate jika model custom: $0.14 input / $0.28 output per 1M
            in_rate = 0.14 / 1_000_000
            out_rate = 0.28 / 1_000_000
        else:
            in_rate = spec.input_price_1m / 1_000_000
            out_rate = spec.output_price_1m / 1_000_000

        # Token biasa bayar penuh, token cache bayar 20% (diskon 80%)
        non_cached_in = max(0, input_tokens - cached_tokens)
        cached_in = cached_tokens

        cost = (non_cached_in * in_rate) + (cached_in * in_rate * 0.2) + (output_tokens * out_rate)
        return round(cost, 6)

    @classmethod
    async def record_usage(cls, record: LLMUsageRecord) -> None:
        """Menyimpan catatan penggunaan ke tabel usage_ledger."""
        record_id = str(uuid.uuid4().hex[:12])
        await db.execute(
            """
            INSERT INTO usage_ledger (
                id, request_id, task_id, role_id, model, provider,
                input_tokens, cached_tokens, reasoning_tokens, output_tokens,
                cost_usd, latency_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                record.request_id,
                record.task_id,
                record.role_id,
                record.model,
                record.provider,
                record.input_tokens,
                record.cached_tokens,
                record.reasoning_tokens,
                record.output_tokens,
                record.cost_usd,
                record.latency_ms,
            ),
        )

    @classmethod
    async def check_thread_budget(cls, group_id: str) -> bool:
        """Memeriksa apakah pengeluaran sesi thread telah melampaui batas budget."""
        row = await db.fetch_one(
            "SELECT SUM(cost_usd) as total_spent FROM usage_ledger"
        )
        total_spent = row["total_spent"] if row and row["total_spent"] else 0.0
        return total_spent < settings.budget_thread_total


usage_meter = UsageMeter()
