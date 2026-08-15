"""Memori terstruktur per grup, per peran, dan audit history."""

import uuid
from typing import Any

from src.core.types import MemoryItem, MemoryScope, MemoryType, RoleID
from src.storage.sqlite import db


class MemoryService:
    @staticmethod
    async def set_memory(
        scope: MemoryScope,
        key: str,
        value: str,
        changed_by_actor: str,
        role_id: RoleID | None = None,
        changed_by_role: RoleID | None = None,
        reason: str | None = None,
        memory_type: MemoryType = MemoryType.FACT,
        group_id: str = "__global__",
    ) -> MemoryItem:
        if scope == MemoryScope.ROLE and role_id is None:
            raise ValueError("role_id wajib untuk role memory")
        role_val = role_id.value if role_id else None

        async with db.transaction() as conn:
            cursor = await conn.execute(
                """SELECT id, value FROM memories
                   WHERE group_id = ? AND scope = ?
                   AND (role_id = ? OR (role_id IS NULL AND ? IS NULL)) AND key = ?""",
                (group_id, scope.value, role_val, role_val, key),
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
                       (id, group_id, scope, role_id, key, value, memory_type)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (mem_id, group_id, scope.value, role_val, key, value, memory_type.value),
                )
            await conn.execute(
                """INSERT INTO memory_audit
                   (id, memory_id, group_id, scope, role_id, key, old_value, new_value,
                    changed_by_actor, changed_by_role, reason)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    f"aud_{uuid.uuid4().hex[:10]}",
                    mem_id,
                    group_id,
                    scope.value,
                    role_val,
                    key,
                    old_value,
                    value,
                    changed_by_actor,
                    changed_by_role.value if changed_by_role else None,
                    reason,
                ),
            )

        return MemoryItem(
            id=mem_id,
            group_id=group_id,
            scope=scope,
            role_id=role_id,
            key=key,
            value=value,
            memory_type=memory_type,
        )

    @staticmethod
    async def get_active_shared_memory(group_id: str = "__global__") -> dict[str, str]:
        rows = await db.fetch_all(
            "SELECT key, value FROM memories WHERE group_id=? AND scope='shared'",
            (group_id,),
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


memory_service = MemoryService()
