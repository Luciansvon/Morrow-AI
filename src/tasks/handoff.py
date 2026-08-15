"""Delegasi tugas dan pelacak rantai oper alih (Anti-Cycle Handoff)."""

import json
import uuid
from typing import Any

from src.core.types import RoleID
from src.storage.sqlite import db
from src.tasks.service import task_service


class TaskHandoffService:
    """Manajer delegasi tugas antar agen (CAP-HANDOFF)."""

    @staticmethod
    async def handoff_task(
        task_id: str,
        from_role: RoleID,
        to_role: RoleID,
        reason: str,
        context_payload: dict[str, Any] | None = None,
    ) -> tuple[bool, str]:
        """
        Mendelegasikan kepemilikan tugas ke agen lain.
        Menerapkan aturan INV-013 & AC-006: DILARANG mengalihkan tugas kembali
        ke agen yang sudah pernah mencoba di rantai delegasi yang sama.
        """
        task = await task_service.get_task(task_id)
        if not task:
            return False, f"Tugas ID '{task_id}' tidak ditemukan."

        # Anti-Cycle Handoff Guard (AC-006)
        if to_role in task.attempted_agents and to_role != task.current_owner:
            return False, f"Anti-Cycle Guard: Tugas dilarang diserahkan kembali ke {to_role.value} yang sudah pernah gagal di rantai delegasi ini!"

        # Catat riwayat handoff
        handoff_id = f"hnd_{uuid.uuid4().hex[:8]}"
        payload_str = json.dumps(context_payload or {})
        await db.execute(
            """
            INSERT INTO task_handoffs (id, task_id, from_role, to_role, reason, context_payload)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (handoff_id, task_id, from_role.value, to_role.value, reason, payload_str),
        )

        # Ubah pemilik tugas saat ini
        await db.execute(
            """
            UPDATE tasks
            SET current_owner = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (to_role.value, task_id),
        )
        return True, f"Tugas berhasil didelegasikan dari {from_role.value} ke {to_role.value}."


task_handoff = TaskHandoffService()
