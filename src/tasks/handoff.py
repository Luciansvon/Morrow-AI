"""Durable task handoff dengan ownership validation dan anti-cycle."""

import json
import uuid
from typing import Any

from src.core.types import RoleID
from src.storage.sqlite import db
from src.tasks.service import task_service


class TaskHandoffService:
    @staticmethod
    async def handoff_task(
        task_id: str,
        from_role: RoleID,
        to_role: RoleID,
        reason: str,
        context_payload: dict[str, Any] | None = None,
    ) -> tuple[bool, str]:
        task = await task_service.get_task(task_id)
        if not task:
            return False, f"Tugas ID '{task_id}' tidak ditemukan."
        if task.current_owner != from_role:
            return False, f"Ownership mismatch: task saat ini dimiliki {task.current_owner.value}."
        if to_role == from_role:
            return False, "Task tidak boleh di-handoff ke owner yang sama."
        if to_role in task.attempted_agents:
            return False, f"Anti-Cycle Guard: Tugas dilarang diserahkan kembali ke {to_role.value} yang sudah pernah berada di rantai ini!"

        handoff_id = f"hnd_{uuid.uuid4().hex[:10]}"
        async with db.transaction() as conn:
            await conn.execute(
                """INSERT INTO task_handoffs
                   (id, task_id, from_role, to_role, reason, context_payload)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (handoff_id, task_id, from_role.value, to_role.value, reason, json.dumps(context_payload or {})),
            )
            await conn.execute(
                "UPDATE tasks SET current_owner=?, status='in_progress', updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (to_role.value, task_id),
            )
        return True, f"Tugas berhasil didelegasikan dari {from_role.value} ke {to_role.value}."


task_handoff = TaskHandoffService()
