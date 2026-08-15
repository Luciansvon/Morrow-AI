"""Lifecycle task dengan retry budget dan status terminal eksplisit."""

import uuid

from src.core.types import RoleID, TaskModel, TaskStatus
from src.storage.sqlite import db


class TaskService:
    @staticmethod
    async def create_task(
        group_id: str,
        title: str,
        description: str = "",
        initial_owner: RoleID = RoleID.MANAGER,
        dependencies: list[str] | None = None,
        max_retries: int = 3,
    ) -> TaskModel:
        task_id = f"task_{uuid.uuid4().hex[:10]}"
        deps = dependencies or []
        if task_id in deps:
            raise ValueError("Task tidak boleh bergantung pada dirinya sendiri")
        for dep_id in deps:
            dep = await TaskService.get_task(dep_id)
            if not dep:
                raise ValueError(f"Dependency '{dep_id}' tidak ditemukan")
            if dep.group_id != group_id:
                raise ValueError("Dependency lintas grup tidak diizinkan")

        async with db.transaction() as conn:
            await conn.execute(
                """INSERT INTO tasks
                   (id, group_id, title, description, current_owner, status, max_retries)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (task_id, group_id, title, description, initial_owner.value, TaskStatus.TODO.value, max_retries),
            )
            for dep_id in deps:
                await conn.execute(
                    "INSERT INTO task_dependencies (task_id, depends_on_task_id) VALUES (?, ?)",
                    (task_id, dep_id),
                )
        return TaskModel(
            id=task_id, group_id=group_id, title=title, description=description,
            current_owner=initial_owner, status=TaskStatus.TODO,
            dependencies=deps, attempted_agents=[initial_owner], max_retries=max_retries,
        )

    @staticmethod
    async def update_task_status(task_id: str, new_status: TaskStatus) -> bool:
        cursor = await db.execute(
            "UPDATE tasks SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (new_status.value, task_id),
        )
        return cursor.rowcount == 1

    @staticmethod
    async def record_failure(task_id: str) -> TaskStatus:
        task = await TaskService.get_task(task_id)
        if not task:
            raise ValueError(f"Task '{task_id}' tidak ditemukan")
        new_count = task.retry_count + 1
        new_status = TaskStatus.BLOCKED if new_count < task.max_retries else TaskStatus.FAILED
        await db.execute(
            "UPDATE tasks SET retry_count=?, status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (new_count, new_status.value, task_id),
        )
        return new_status

    @staticmethod
    async def get_task(task_id: str) -> TaskModel | None:
        row = await db.fetch_one("SELECT * FROM tasks WHERE id=?", (task_id,))
        if not row:
            return None
        deps = [
            r["depends_on_task_id"]
            for r in await db.fetch_all(
                "SELECT depends_on_task_id FROM task_dependencies WHERE task_id=?",
                (task_id,),
            )
        ]
        handoffs = await db.fetch_all(
            "SELECT from_role, to_role FROM task_handoffs WHERE task_id=? ORDER BY created_at ASC",
            (task_id,),
        )
        attempted: list[RoleID] = []
        for hr in handoffs:
            for value in (hr["from_role"], hr["to_role"]):
                role = RoleID(value)
                if role not in attempted:
                    attempted.append(role)
        owner = RoleID(row["current_owner"])
        if owner not in attempted:
            attempted.append(owner)
        return TaskModel(
            id=row["id"], group_id=row["group_id"], title=row["title"],
            description=row["description"] or "", current_owner=owner,
            status=TaskStatus(row["status"]), dependencies=deps,
            attempted_agents=attempted, retry_count=row["retry_count"],
            max_retries=row.get("max_retries", 3) or 3,
        )

    @staticmethod
    async def list_active_tasks(group_id: str) -> list[TaskModel]:
        rows = await db.fetch_all(
            """SELECT id FROM tasks WHERE group_id=?
               AND status IN ('todo','in_progress','blocked','waiting_user')""",
            (group_id,),
        )
        result = []
        for row in rows:
            task = await TaskService.get_task(row["id"])
            if task:
                result.append(task)
        return result


task_service = TaskService()
