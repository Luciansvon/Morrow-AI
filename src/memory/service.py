"""Layanan penyimpanan memori peran, memori bersama, dan audit history."""

import uuid
from typing import Any

from src.core.types import MemoryItem, MemoryScope, MemoryType, RoleID
from src.storage.sqlite import db


class MemoryService:
    """Manajer memori terstruktur Morrow v0.2 (CAP-MEMORY)."""

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
    ) -> MemoryItem:
        """
        Menulis nilai memori baru. Jika nilai lama sudah ada, nilai lama dicatat
        ke tabel memory_audit sebelum digantikan (AC-010).
        """
        role_val = role_id.value if role_id else None
        existing = await db.fetch_one(
            """
            SELECT id, value FROM memories
            WHERE scope = ? AND (role_id = ? OR (role_id IS NULL AND ? IS NULL)) AND key = ?
            """,
            (scope.value, role_val, role_val, key),
        )

        old_value = None
        if existing:
            mem_id = existing["id"]
            old_value = existing["value"]
            await db.execute(
                """
                UPDATE memories
                SET value = ?, memory_type = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (value, memory_type.value, mem_id),
            )
        else:
            mem_id = f"mem_{uuid.uuid4().hex[:8]}"
            await db.execute(
                """
                INSERT INTO memories (id, scope, role_id, key, value, memory_type)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (mem_id, scope.value, role_val, key, value, memory_type.value),
            )

        # Catat ke memory_audit jika terjadi pembaruan nilai atau pembuatan baru
        audit_id = f"aud_{uuid.uuid4().hex[:8]}"
        await db.execute(
            """
            INSERT INTO memory_audit (
                id, memory_id, scope, role_id, key, old_value, new_value,
                changed_by_actor, changed_by_role, reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                audit_id,
                mem_id,
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
            scope=scope,
            role_id=role_id,
            key=key,
            value=value,
            memory_type=memory_type,
        )

    @staticmethod
    async def get_active_shared_memory() -> dict[str, str]:
        """Mengambil seluruh fakta/keputusan aktif dalam memori bersama."""
        rows = await db.fetch_all(
            "SELECT key, value FROM memories WHERE scope = 'shared'"
        )
        return {r["key"]: r["value"] for r in rows}

    @staticmethod
    async def get_role_memory(role: RoleID) -> dict[str, str]:
        """Mengambil catatan memori internal spesifik peran."""
        rows = await db.fetch_all(
            "SELECT key, value FROM memories WHERE scope = 'role' AND role_id = ?",
            (role.value,),
        )
        return {r["key"]: r["value"] for r in rows}

    @staticmethod
    async def get_memory_audit_history(key: str) -> list[dict[str, Any]]:
        """Mengambil riwayat perubahan nilai lampau suatu keputusan (AC-010)."""
        rows = await db.fetch_all(
            "SELECT * FROM memory_audit WHERE key = ? ORDER BY timestamp ASC",
            (key,),
        )
        return rows


memory_service = MemoryService()
