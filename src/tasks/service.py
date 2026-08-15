"""Layanan siklus hidup tugas terstruktur (Task Lifecycle Service)."""

import uuid

from src.core.types import RoleID, TaskModel, TaskStatus
from src.storage.sqlite import db


class TaskService:
    """Manajer siklus hidup tugas: todo, in_progress, blocked, done, cancelled."""

    @staticmethod
    async def create_task(
        group_id: str,
        title: str,
        description: str = "",
        initial_owner: RoleID = RoleID.MANAGER,
        dependencies: list[str] | None = None,
    ) -> TaskModel:
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        await db.execute(
            """
            INSERT INTO tasks (id, group_id, title, description, current_owner, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (task_id, group_id, title, description, initial_owner.value, TaskStatus.TODO.value),
        )

        deps = dependencies or []
        for dep_id in deps:
            await db.execute(
                "INSERT INTO task_dependencies (task_id, depends_on_task_id) VALUES (?, ?)",
                (task_id, dep_id),
            )

        return TaskModel(
            id=task_id,
            title=title,
            description=description,
            current_owner=initial_owner,
            status=TaskStatus.TODO,
            dependencies=deps,
            attempted_agents=[initial_owner],
        )

    @staticmethod
    async def update_task_status(task_id: str, new_status: TaskStatus) -> bool:
        await db.execute(
            "UPDATE tasks SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (new_status.value, task_id),
        )
        return True

    @staticmethod
    async def get_task(task_id: str) -> TaskModel | None:
        row = await db.fetch_one("SELECT * FROM tasks WHERE id = ?", (task_id,))
        if not row:
            return None

        # Ambil daftar dependensi
        dep_rows = await db.fetch_all(
            "SELECT depends_on_task_id FROM task_dependencies WHERE task_id = ?",
            (task_id,),
        )
        deps = [r["depends_on_task_id"] for r in dep_rows]

        # Ambil jejak attempted agents dari riwayat handoff (from_role dan to_role)
        handoff_rows = await db.fetch_all(
            "SELECT from_role, to_role FROM task_handoffs WHERE task_id = ? ORDER BY created_at ASC",
            (task_id,),
        )
        attempted = []
        for hr in handoff_rows:
            f_r = RoleID(hr["from_role"])
            t_r = RoleID(hr["to_role"])
            if f_r not in attempted:
                attempted.append(f_r)
            if t_r not in attempted:
                attempted.append(t_r)

        cur_r = RoleID(row["current_owner"])
        if cur_r not in attempted:
            attempted.append(cur_r)

        return TaskModel(
            id=row["id"],
            title=row["title"],
            description=row["description"] or "",
            current_owner=cur_r,
            status=TaskStatus(row["status"]),
            dependencies=deps,
            attempted_agents=attempted,
            retry_count=row["retry_count"],
        )

    @staticmethod
    async def list_active_tasks(group_id: str) -> list[TaskModel]:
        rows = await db.fetch_all(
            "SELECT id FROM tasks WHERE group_id = ? AND status IN ('todo', 'in_progress', 'blocked')",
            (group_id,),
        )
        tasks = []
        for r in rows:
            t = await TaskService.get_task(r["id"])
            if t:
                tasks.append(t)
        return tasks


task_service = TaskService()
