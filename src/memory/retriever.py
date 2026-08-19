"""Bounded hybrid retrieval: query-relevant structured truth + FTS5 + sqlite-vec RRF."""

import asyncio
import re
from typing import Any

from src.core.config import settings
from src.core.types import RoleID
from src.memory.vector_index import memory_vector_index
from src.storage.sqlite import db

_QUERY_TOKEN_RE = re.compile(r"\w+", re.UNICODE)
_GENERIC_QUERY_TOKENS = {
    "apa", "apakah", "bagaimana", "gimana", "kenapa", "kok", "terus", "lanjut",
    "lanjutkan", "udah", "sudah", "belum", "dong", "nih", "tadi", "yang", "ini", "itu",
    "dan", "atau", "dengan", "untuk", "dari", "kita", "saya", "aku", "gua", "gue", "lu",
    "kamu", "tolong", "bantu", "cek", "lihat", "update", "status", "progress", "progres",
    "keputusan", "decision", "fakta", "fact", "batasan", "constraint", "ingat", "memori",
}


class HybridMemoryRetriever:
    @staticmethod
    def _meaningful_tokens(text: str) -> list[str]:
        tokens: list[str] = []
        for token in _QUERY_TOKEN_RE.findall((text or "").lower()):
            if len(token) < 2 or token in _GENERIC_QUERY_TOKENS or token in tokens:
                continue
            tokens.append(token)
            if len(tokens) >= 20:
                break
        return tokens

    @classmethod
    def _fts_query(cls, text: str) -> str | None:
        tokens = cls._meaningful_tokens(text)[:12]
        if not tokens:
            return None
        return " OR ".join(f'"{token}"' for token in tokens)

    @classmethod
    async def _fts_search(
        cls,
        query: str,
        group_id: str,
        role: RoleID,
        user_id: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        match_query = cls._fts_query(query)
        if not match_query:
            return []
        try:
            return await db.fetch_all(
                """SELECT memory_fts.memory_id AS id, memory_fts.group_id,
                          memory_fts.scope, memory_fts.role_id, m.user_id,
                          memory_fts.key, memory_fts.value, memory_fts.memory_type,
                          bm25(memory_fts, 0.0, 0.0, 0.0, 0.0, 4.0, 1.0, 0.0) AS fts_rank
                   FROM memory_fts
                   JOIN memories m ON m.id=memory_fts.memory_id
                   WHERE memory_fts MATCH ? AND memory_fts.group_id=?
                     AND (
                         memory_fts.scope='shared'
                         OR (memory_fts.scope='role' AND memory_fts.role_id=?)
                         OR (memory_fts.scope='user' AND m.user_id=?)
                     )
                   ORDER BY fts_rank
                   LIMIT ?""",
                (match_query, group_id, role.value, user_id, limit),
            )
        except Exception:
            return []

    @classmethod
    async def _pinned_truth(
        cls,
        query: str,
        group_id: str,
        role: RoleID,
        user_id: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Prioritize decisions/constraints only when they overlap the current topic."""
        query_tokens = set(cls._meaningful_tokens(query))
        if not query_tokens:
            return []
        rows = await db.fetch_all(
            """SELECT id, group_id, scope, role_id, user_id, key, value, memory_type,
                      updated_at, created_at
               FROM memories
               WHERE group_id=?
                 AND memory_type IN ('decision','constraint')
                 AND (
                     scope='shared'
                     OR (scope='role' AND role_id=?)
                     OR (scope='user' AND user_id=?)
                 )
               ORDER BY updated_at DESC, created_at DESC
               LIMIT 50""",
            (group_id, role.value, user_id),
        )
        ranked: list[tuple[int, int, dict[str, Any]]] = []
        for recency, row in enumerate(rows):
            row_tokens = set(cls._meaningful_tokens(f"{row.get('key', '')} {row.get('value', '')}"))
            overlap = len(query_tokens & row_tokens)
            if overlap > 0:
                ranked.append((overlap, -recency, row))
        ranked.sort(key=lambda item: (-item[0], -item[1]))
        return [row for _, _, row in ranked[:limit]]

    async def retrieve(
        self,
        query: str,
        group_id: str,
        role: RoleID,
        limit: int | None = None,
        *,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        if not self._meaningful_tokens(query):
            return []

        top_k = settings.memory_hybrid_top_k if limit is None else max(1, limit)
        candidate_k = min(50, max(top_k * 2, 8))
        pinned_task = self._pinned_truth(query, group_id, role, user_id, min(4, top_k))
        fts_task = self._fts_search(query, group_id, role, user_id, candidate_k)
        semantic_task = memory_vector_index.search(
            query,
            group_id,
            role,
            candidate_k,
            user_id=user_id,
        )
        pinned, fts_rows, semantic_rows = await asyncio.gather(
            pinned_task,
            fts_task,
            semantic_task,
        )

        merged: dict[str, dict[str, Any]] = {}
        score: dict[str, float] = {}
        for row in pinned:
            memory_id = row["id"]
            merged[memory_id] = row
            score[memory_id] = score.get(memory_id, 0.0) + 1.0
        for rank, row in enumerate(fts_rows, start=1):
            memory_id = row["id"]
            merged.setdefault(memory_id, row)
            score[memory_id] = score.get(memory_id, 0.0) + 1.0 / (60 + rank)
        for rank, row in enumerate(semantic_rows, start=1):
            memory_id = row["id"]
            merged.setdefault(memory_id, row)
            score[memory_id] = score.get(memory_id, 0.0) + 1.0 / (60 + rank)

        ordered = sorted(
            merged.values(),
            key=lambda row: (-score[row["id"]], row["key"]),
        )
        return ordered[:top_k]


hybrid_memory_retriever = HybridMemoryRetriever()
