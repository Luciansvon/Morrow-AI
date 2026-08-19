"""Durable structured memory with fail-soft derived retrieval indexes."""

import uuid
from typing import Any

from src.core.request_context import current_user_id
from src.core.types import MemoryItem, MemoryScope, MemoryType, RoleID
from src.memory.retriever import hybrid_memory_retriever
from src.memory.vault import memory_vault
from src.memory.vector_index import memory_vector_index
from src.storage.sqlite import db


class MemoryService:
    @staticmethod
    async def set_memory(
        scope: MemoryScope,
        key: str,
        value: str,
        changed_by_actor: str,
        role_id: RoleID | None = None,
        user_id: str | None = None,
        changed_by_role: RoleID | None = None,
        reason: str | None = None,
        memory_type: MemoryType = MemoryType.FACT,
        group_id: str = "__global__",
    ) -> MemoryItem:
        if scope == MemoryScope.USER:
            if not (user_id or "").strip():
                raise ValueError("user_id wajib untuk user memory")
            if role_id is not None:
                raise ValueError("role_id tidak boleh diisi untuk user memory")
        elif scope == MemoryScope.ROLE:
            if role_id is None:
                raise ValueError("role_id wajib untuk role memory")
            if user_id is not None:
                raise ValueError("user_id tidak boleh diisi untuk role memory")
        elif scope == MemoryScope.SHARED:
            if role_id is not None or user_id is not None:
                raise ValueError("role_id/user_id tidak boleh diisi untuk shared memory")

        role_val = role_id.value if role_id else None
        user_val = user_id.strip() if user_id else None

        async with db.transaction() as conn:
            cursor = await conn.execute(
                """SELECT id, value FROM memories
                   WHERE group_id=? AND scope=?
                     AND (role_id=? OR (role_id IS NULL AND ? IS NULL))
                     AND (user_id=? OR (user_id IS NULL AND ? IS NULL))
                     AND key=?""",
                (group_id, scope.value, role_val, role_val, user_val, user_val, key),
            )
            raw = await cursor.fetchone()
            existing = dict(raw) if raw else None
            old_value = existing["value"] if existing else None
            mem_id = existing["id"] if existing else f"mem_{uuid.uuid4().hex[:10]}"

            if existing:
                await conn.execute(
                    """UPDATE memories
                       SET value=?, memory_type=?, updated_at=CURRENT_TIMESTAMP
                       WHERE id=?""",
                    (value, memory_type.value, mem_id),
                )
            else:
                await conn.execute(
                    """INSERT INTO memories
                       (id, group_id, scope, role_id, user_id, key, value, memory_type)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        mem_id,
                        group_id,
                        scope.value,
                        role_val,
                        user_val,
                        key,
                        value,
                        memory_type.value,
                    ),
                )
            await conn.execute(
                """INSERT INTO memory_audit
                   (id, memory_id, group_id, scope, role_id, user_id, key, old_value, new_value,
                    changed_by_actor, changed_by_role, reason)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    f"aud_{uuid.uuid4().hex[:10]}",
                    mem_id,
                    group_id,
                    scope.value,
                    role_val,
                    user_val,
                    key,
                    old_value,
                    value,
                    changed_by_actor,
                    changed_by_role.value if changed_by_role else None,
                    reason,
                ),
            )

        item = MemoryItem(
            id=mem_id,
            group_id=group_id,
            scope=scope,
            role_id=role_id,
            user_id=user_val,
            key=key,
            value=value,
            memory_type=memory_type,
        )

        # Derived indexes must never make the source-of-truth write fail.
        try:
            await memory_vault.sync_scope(group_id, scope, role_id, user_val)
        except Exception:
            pass
        try:
            await memory_vector_index.index_memory(item)
        except Exception:
            pass
        return item

    @staticmethod
    async def get_active_shared_memory(group_id: str = "__global__") -> dict[str, str]:
        rows = await db.fetch_all(
            "SELECT key, value FROM memories WHERE group_id=? AND scope='shared'",
            (group_id,),
        )
        return {row["key"]: row["value"] for row in rows}

    @staticmethod
    async def get_user_memory(user_id: str, group_id: str = "__global__") -> dict[str, str]:
        rows = await db.fetch_all(
            """SELECT key, value FROM memories
               WHERE group_id=? AND scope='user' AND user_id=?""",
            (group_id, user_id),
        )
        return {row["key"]: row["value"] for row in rows}

    @staticmethod
    async def get_role_memory(role: RoleID, group_id: str = "__global__") -> dict[str, str]:
        rows = await db.fetch_all(
            "SELECT key, value FROM memories WHERE group_id=? AND scope='role' AND role_id=?",
            (group_id, role.value),
        )
        return {row["key"]: row["value"] for row in rows}

    @staticmethod
    async def get_memory_audit_history(
        key: str,
        group_id: str = "__global__",
    ) -> list[dict[str, Any]]:
        return await db.fetch_all(
            "SELECT * FROM memory_audit WHERE group_id=? AND key=? ORDER BY timestamp ASC",
            (group_id, key),
        )

    @staticmethod
    async def retrieve_relevant_memory(
        query: str,
        role: RoleID,
        group_id: str = "__global__",
        limit: int | None = None,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        effective_user_id = user_id or current_user_id()
        return await hybrid_memory_retriever.retrieve(
            query,
            group_id,
            role,
            limit,
            user_id=effective_user_id,
        )

    @staticmethod
    async def initialize_long_term_memory() -> dict[str, int]:
        mirrored = 0
        indexed = 0
        try:
            mirrored = await memory_vault.sync_all()
        except Exception:
            pass
        try:
            indexed = await memory_vector_index.backfill()
        except Exception:
            pass
        return {"markdown_scopes": mirrored, "semantic_memories": indexed}


memory_service = MemoryService()
