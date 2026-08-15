"""Derived sqlite-vec index for semantic long-term-memory retrieval."""

import hashlib
import json
import logging
from typing import Any

from src.core.config import settings
from src.core.types import MemoryItem, RoleID
from src.memory.embeddings import memory_embedding_provider
from src.storage.sqlite import db

logger = logging.getLogger(__name__)


class MemoryVectorIndex:
    @staticmethod
    def _document_text(key: str, value: str) -> str:
        return f"{key}\n{value}"[: settings.memory_embedding_max_chars]

    @classmethod
    def _content_hash(cls, key: str, value: str) -> str:
        text = cls._document_text(key, value)
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    async def _upsert_vector(
        memory_id: str,
        group_id: str,
        scope: str,
        role_id: str,
        content_hash: str,
        embedding: list[float],
    ) -> None:
        model = settings.memory_embedding_model
        dimensions = settings.memory_embedding_dimensions
        async with db.transaction() as conn:
            cursor = await conn.execute(
                "SELECT vector_id FROM memory_vector_map WHERE memory_id=?",
                (memory_id,),
            )
            raw = await cursor.fetchone()
            if raw:
                vector_id = int(raw["vector_id"])
                await conn.execute("DELETE FROM memory_vec WHERE vector_id=?", (vector_id,))
                await conn.execute(
                    """UPDATE memory_vector_map
                       SET content_hash=?, model=?, dimensions=?, updated_at=CURRENT_TIMESTAMP
                       WHERE memory_id=?""",
                    (content_hash, model, dimensions, memory_id),
                )
            else:
                inserted = await conn.execute(
                    """INSERT INTO memory_vector_map(memory_id, content_hash, model, dimensions)
                       VALUES (?, ?, ?, ?)""",
                    (memory_id, content_hash, model, dimensions),
                )
                vector_id = int(inserted.lastrowid)
            await conn.execute(
                """INSERT INTO memory_vec(vector_id, embedding, group_id, scope, role_id)
                   VALUES (?, ?, ?, ?, ?)""",
                (vector_id, json.dumps(embedding), group_id, scope, role_id),
            )

    async def index_memory(self, item: MemoryItem) -> bool:
        if not settings.memory_semantic_enabled or not db.vector_extension_loaded:
            return False
        content_hash = self._content_hash(item.key, item.value)
        existing = await db.fetch_one(
            """SELECT content_hash, model, dimensions FROM memory_vector_map
               WHERE memory_id=?""",
            (item.id,),
        )
        if (
            existing
            and existing["content_hash"] == content_hash
            and existing["model"] == settings.memory_embedding_model
            and int(existing["dimensions"]) == settings.memory_embedding_dimensions
        ):
            return True

        embedding = await memory_embedding_provider.embed_text(
            self._document_text(item.key, item.value)
        )
        if embedding is None:
            return False
        try:
            await self._upsert_vector(
                memory_id=item.id,
                group_id=item.group_id,
                scope=item.scope.value,
                role_id=item.role_id.value if item.role_id else "",
                content_hash=content_hash,
                embedding=embedding,
            )
        except Exception:
            return False
        return True

    async def backfill(self, limit: int | None = None) -> int:
        if not settings.memory_semantic_enabled or not db.vector_extension_loaded:
            return 0
        max_items = settings.memory_semantic_backfill_limit if limit is None else max(0, limit)
        if max_items == 0:
            return 0
        rows = await db.fetch_all(
            """SELECT m.id, m.group_id, m.scope, m.role_id, m.key, m.value,
                      vm.content_hash, vm.model, vm.dimensions
               FROM memories m
               LEFT JOIN memory_vector_map vm ON vm.memory_id=m.id
               ORDER BY m.updated_at DESC, m.created_at DESC
               LIMIT ?""",
            (max_items,),
        )
        stale: list[dict[str, Any]] = []
        texts: list[str] = []
        for row in rows:
            content_hash = self._content_hash(row["key"], row["value"])
            current = (
                row["content_hash"] == content_hash
                and row["model"] == settings.memory_embedding_model
                and int(row["dimensions"] or 0) == settings.memory_embedding_dimensions
            )
            if current:
                continue
            stale.append({**row, "new_content_hash": content_hash})
            texts.append(self._document_text(row["key"], row["value"]))

        embeddings = await memory_embedding_provider.embed_texts(texts)
        if not embeddings or len(embeddings) != len(stale):
            return 0
        indexed = 0
        for row, embedding in zip(stale, embeddings, strict=True):
            try:
                await self._upsert_vector(
                    memory_id=row["id"],
                    group_id=row["group_id"],
                    scope=row["scope"],
                    role_id=row["role_id"] or "",
                    content_hash=row["new_content_hash"],
                    embedding=embedding,
                )
            except Exception:
                logger.exception("Gagal backfill vector memory %s", row["id"])
            else:
                indexed += 1
        return indexed

    @staticmethod
    async def _nearest_ids(
        embedding: list[float],
        group_id: str,
        scope: str,
        role_id: str | None,
        limit: int,
    ) -> list[tuple[int, float]]:
        role_clause = " AND role_id=?" if role_id is not None else ""
        params: tuple[Any, ...] = (
            json.dumps(embedding),
            group_id,
            scope,
            *((role_id,) if role_id is not None else ()),
            limit,
        )
        rows = await db.fetch_all(
            f"""SELECT vector_id, distance FROM memory_vec
                WHERE embedding MATCH ? AND group_id=? AND scope=?{role_clause} AND k=?
                ORDER BY distance""",
            params,
        )
        return [(int(row["vector_id"]), float(row["distance"])) for row in rows]

    async def search(
        self,
        query: str,
        group_id: str,
        role: RoleID,
        limit: int,
    ) -> list[dict[str, Any]]:
        if not query.strip() or not settings.memory_semantic_enabled or not db.vector_extension_loaded:
            return []
        embedding = await memory_embedding_provider.embed_text(query)
        if embedding is None:
            return []
        try:
            candidates = await self._nearest_ids(embedding, group_id, "shared", None, limit)
            candidates += await self._nearest_ids(
                embedding,
                group_id,
                "role",
                role.value,
                limit,
            )
        except Exception:
            return []
        if not candidates:
            return []

        best_distance: dict[int, float] = {}
        for vector_id, distance in candidates:
            best_distance[vector_id] = min(distance, best_distance.get(vector_id, distance))
        vector_ids = list(best_distance)
        placeholders = ",".join("?" for _ in vector_ids)
        rows = await db.fetch_all(
            f"""SELECT vm.vector_id, m.id, m.group_id, m.scope, m.role_id,
                       m.key, m.value, m.memory_type
                FROM memory_vector_map vm
                JOIN memories m ON m.id=vm.memory_id
                WHERE vm.vector_id IN ({placeholders})""",
            tuple(vector_ids),
        )
        for row in rows:
            row["semantic_distance"] = best_distance[int(row["vector_id"])]
        rows.sort(key=lambda row: row["semantic_distance"])
        return rows[:limit]


memory_vector_index = MemoryVectorIndex()
