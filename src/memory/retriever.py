"""Bounded hybrid retrieval: pinned structured truth + FTS5 + sqlite-vec RRF."""

import asyncio
import re
from typing import Any

from src.core.config import settings
from src.core.types import RoleID
from src.memory.vector_index import memory_vector_index
from src.storage.sqlite import db

_QUERY_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


class HybridMemoryRetriever:
    @staticmethod
    def _fts_query(text: str) -> str | None:
        tokens: list[str] = []
        for token in _QUERY_TOKEN_RE.findall(text.lower()):
            if len(token) < 2 or token in tokens:
                continue
            tokens.append(token)
            if len(tokens) >= 12:
                break
        if not tokens:
            return None
        return " OR ".join(f'"{token}"' for token in tokens)

    @classmethod
    async def _fts_search(
        cls,
        query: str,
        group_id: str,
        role: RoleID,
        limit: int,
    ) -> list[dict[str, Any]]:
        match_query = cls._fts_query(query)
        if not match_query:
            return []
        try:
            return await db.fetch_all(
                """SELECT memory_id AS id, group_id, scope, role_id, key, value, memory_type,
                          bm25(memory_fts, 0.0, 0.0, 0.0, 0.0, 4.0, 1.0, 0.0) AS fts_rank
                   FROM memory_fts
                   WHERE memory_fts MATCH ? AND group_id=?
                     AND (scope='shared' OR (scope='role' AND role_id=?))
                   ORDER BY fts_rank
                   LIMIT ?""",
                (match_query, group_id, role.value, limit),
            )
        except Exception:
            return []

    @staticmethod
    async def _pinned_truth(
        group_id: str,
        role: RoleID,
        limit: int,
    ) -> list[dict[str, Any]]:
        return await db.fetch_all(
            """SELECT id, group_id, scope, role_id, key, value, memory_type
               FROM memories
               WHERE group_id=?
                 AND memory_type IN ('decision','constraint')
                 AND (scope='shared' OR (scope='role' AND role_id=?))
               ORDER BY updated_at DESC, created_at DESC
               LIMIT ?""",
            (group_id, role.value, limit),
        )

    async def retrieve(
        self,
        query: str,
        group_id: str,
        role: RoleID,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        top_k = settings.memory_hybrid_top_k if limit is None else max(1, limit)
        candidate_k = min(50, max(top_k * 2, 8))
        pinned_task = self._pinned_truth(group_id, role, min(4, top_k))
        fts_task = self._fts_search(query, group_id, role, candidate_k)
        semantic_task = memory_vector_index.search(query, group_id, role, candidate_k)
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
