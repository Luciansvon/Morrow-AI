"""Durable task handoff dengan ownership validation dan atomic anti-cycle."""

import json
import uuid
from typing import Any

from src.core.types import RoleID, TaskStatus
from src.storage.sqlite import db


class TaskHandoffService:
    @staticmethod
    async def handoff_task(
        task_id: str,
        from_role: RoleID,
        to_role: RoleID,
        reason: str,
        context_payload: dict[str, Any] | None = None,
    ) -> tuple[bool, str]:
        if to_role == from_role:
            return False, "Task tidak boleh di-handoff ke owner yang sama."

        async with db.transaction() as conn:
            cursor = await conn.execute(
                "SELECT current_owner, status FROM tasks WHERE id=?",
                (task_id,),
            )
            raw = await cursor.fetchone()
            if not raw:
                return False, f"Tugas ID '{task_id}' tidak ditemukan."
            current_owner = RoleID(raw["current_owner"])
            if current_owner != from_role:
                return False, f"Ownership mismatch: task saat ini dimiliki {current_owner.value}."

            current_status = TaskStatus(raw["status"])
            if current_status in {TaskStatus.DONE, TaskStatus.FAILED, TaskStatus.CANCELLED}:
                return False, (
                    "Task terminal tidak boleh di-handoff atau dibuka kembali: "
                    f"status={current_status.value}."
                )

            cursor = await conn.execute(
                """SELECT d.depends_on_task_id, t.status
                   FROM task_dependencies d
                   LEFT JOIN tasks t ON t.id=d.depends_on_task_id
                   WHERE d.task_id=? AND (t.status IS NULL OR t.status!='done')""",
                (task_id,),
            )
            incomplete = [str(row["depends_on_task_id"]) for row in await cursor.fetchall()]
            if incomplete:
                return False, (
                    "Task belum boleh di-handoff ke eksekusi karena dependency belum selesai: "
                    + ", ".join(incomplete)
                )

            cursor = await conn.execute(
                "SELECT from_role, to_role FROM task_handoffs WHERE task_id=?",
                (task_id,),
            )
            handoffs = await cursor.fetchall()
            attempted = {from_role}
            for handoff in handoffs:
                attempted.add(RoleID(handoff["from_role"]))
                attempted.add(RoleID(handoff["to_role"]))
            if to_role in attempted:
                return False, (
                    "Anti-Cycle Guard: Tugas dilarang diserahkan kembali ke "
                    f"{to_role.value} yang sudah pernah berada di rantai ini!"
                )

            handoff_id = f"hnd_{uuid.uuid4().hex[:10]}"
            await conn.execute(
                """INSERT INTO task_handoffs
                   (id, task_id, from_role, to_role, reason, context_payload)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    handoff_id,
                    task_id,
                    from_role.value,
                    to_role.value,
                    reason,
                    json.dumps(context_payload or {}),
                ),
            )
            updated = await conn.execute(
                """UPDATE tasks
                   SET current_owner=?, status='in_progress', updated_at=CURRENT_TIMESTAMP
                   WHERE id=? AND current_owner=?
                     AND status NOT IN ('done','failed','cancelled')""",
                (to_role.value, task_id, from_role.value),
            )
            if updated.rowcount != 1:
                raise RuntimeError("Task ownership/status berubah saat handoff berlangsung.")
        return True, f"Tugas berhasil didelegasikan dari {from_role.value} ke {to_role.value}."


task_handoff = TaskHandoffService()
