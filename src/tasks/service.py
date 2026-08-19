"""Lifecycle task dengan dependency gate, retry budget, dan per-agent run ledger."""

import uuid

from src.core.types import RoleID, TaskModel, TaskStatus
from src.storage.sqlite import db

_TERMINAL_STATUSES = {TaskStatus.DONE, TaskStatus.FAILED, TaskStatus.CANCELLED}
_ALLOWED_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.TODO: {
        TaskStatus.IN_PROGRESS,
        TaskStatus.BLOCKED,
        TaskStatus.WAITING_USER,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
    },
    TaskStatus.IN_PROGRESS: {
        TaskStatus.BLOCKED,
        TaskStatus.WAITING_USER,
        TaskStatus.DONE,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
    },
    TaskStatus.BLOCKED: {
        TaskStatus.TODO,
        TaskStatus.IN_PROGRESS,
        TaskStatus.WAITING_USER,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
    },
    TaskStatus.WAITING_USER: {
        TaskStatus.TODO,
        TaskStatus.IN_PROGRESS,
        TaskStatus.CANCELLED,
    },
    TaskStatus.DONE: set(),
    TaskStatus.FAILED: set(),
    TaskStatus.CANCELLED: set(),
}


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
        if max_retries < 1:
            raise ValueError("max_retries harus minimal 1")
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
                (
                    task_id,
                    group_id,
                    title,
                    description,
                    initial_owner.value,
                    TaskStatus.TODO.value,
                    max_retries,
                ),
            )
            for dep_id in deps:
                await conn.execute(
                    "INSERT INTO task_dependencies (task_id, depends_on_task_id) VALUES (?, ?)",
                    (task_id, dep_id),
                )
        return TaskModel(
            id=task_id,
            group_id=group_id,
            title=title,
            description=description,
            current_owner=initial_owner,
            status=TaskStatus.TODO,
            dependencies=deps,
            attempted_agents=[initial_owner],
            max_retries=max_retries,
        )

    @staticmethod
    async def _dependencies_done(conn, task_id: str) -> tuple[bool, list[str]]:
        cursor = await conn.execute(
            """SELECT d.depends_on_task_id, t.status
               FROM task_dependencies d
               LEFT JOIN tasks t ON t.id=d.depends_on_task_id
               WHERE d.task_id=?""",
            (task_id,),
        )
        rows = await cursor.fetchall()
        incomplete = [
            str(row["depends_on_task_id"])
            for row in rows
            if row["status"] != TaskStatus.DONE.value
        ]
        return not incomplete, incomplete

    @staticmethod
    async def update_task_status(task_id: str, new_status: TaskStatus) -> bool:
        async with db.transaction() as conn:
            cursor = await conn.execute("SELECT status FROM tasks WHERE id=?", (task_id,))
            raw = await cursor.fetchone()
            if not raw:
                return False
            current = TaskStatus(raw["status"])
            if current == new_status:
                return True
            if current in _TERMINAL_STATUSES:
                return False
            if new_status not in _ALLOWED_TRANSITIONS[current]:
                return False
            if new_status in {TaskStatus.IN_PROGRESS, TaskStatus.DONE}:
                dependencies_done, _ = await TaskService._dependencies_done(conn, task_id)
                if not dependencies_done:
                    return False
            cursor = await conn.execute(
                """UPDATE tasks SET status=?, updated_at=CURRENT_TIMESTAMP
                   WHERE id=? AND status=?""",
                (new_status.value, task_id, current.value),
            )
            return cursor.rowcount == 1

    @staticmethod
    async def cancel_task(task_id: str) -> bool:
        async with db.transaction() as conn:
            cursor = await conn.execute(
                """UPDATE tasks SET status='cancelled', updated_at=CURRENT_TIMESTAMP
                   WHERE id=? AND status IN ('todo','in_progress','blocked','waiting_user')""",
                (task_id,),
            )
            if cursor.rowcount != 1:
                return False
            await conn.execute(
                """UPDATE task_agent_runs
                   SET status='cancelled', finished_at=CURRENT_TIMESTAMP
                   WHERE task_id=? AND status='running'""",
                (task_id,),
            )
            return True

    @staticmethod
    async def pause_task(task_id: str) -> bool:
        async with db.transaction() as conn:
            cursor = await conn.execute(
                """UPDATE tasks SET status='waiting_user', updated_at=CURRENT_TIMESTAMP
                   WHERE id=? AND status IN ('todo','in_progress','blocked')""",
                (task_id,),
            )
            if cursor.rowcount != 1:
                return False
            await conn.execute(
                """UPDATE task_agent_runs
                   SET status='cancelled', finished_at=CURRENT_TIMESTAMP
                   WHERE task_id=? AND status='running'""",
                (task_id,),
            )
            return True

    @staticmethod
    async def cancel_active_tasks(group_id: str) -> int:
        async with db.transaction() as conn:
            cursor = await conn.execute(
                """SELECT id FROM tasks
                   WHERE group_id=? AND status IN ('todo','in_progress','blocked','waiting_user')""",
                (group_id,),
            )
            task_ids = [str(row["id"]) for row in await cursor.fetchall()]
            if not task_ids:
                return 0
            placeholders = ",".join("?" for _ in task_ids)
            await conn.execute(
                f"""UPDATE tasks SET status='cancelled', updated_at=CURRENT_TIMESTAMP
                    WHERE id IN ({placeholders})""",
                tuple(task_ids),
            )
            await conn.execute(
                f"""UPDATE task_agent_runs
                    SET status='cancelled', finished_at=CURRENT_TIMESTAMP
                    WHERE task_id IN ({placeholders}) AND status='running'""",
                tuple(task_ids),
            )
            return len(task_ids)

    @staticmethod
    async def pause_active_tasks(group_id: str) -> int:
        async with db.transaction() as conn:
            cursor = await conn.execute(
                """SELECT id FROM tasks
                   WHERE group_id=? AND status IN ('todo','in_progress','blocked')""",
                (group_id,),
            )
            task_ids = [str(row["id"]) for row in await cursor.fetchall()]
            if not task_ids:
                return 0
            placeholders = ",".join("?" for _ in task_ids)
            await conn.execute(
                f"""UPDATE tasks SET status='waiting_user', updated_at=CURRENT_TIMESTAMP
                    WHERE id IN ({placeholders})""",
                tuple(task_ids),
            )
            await conn.execute(
                f"""UPDATE task_agent_runs
                    SET status='cancelled', finished_at=CURRENT_TIMESTAMP
                    WHERE task_id IN ({placeholders}) AND status='running'""",
                tuple(task_ids),
            )
            return len(task_ids)

    @staticmethod
    async def resume_waiting_tasks(group_id: str) -> int:
        cursor = await db.execute(
            """UPDATE tasks SET status='todo', updated_at=CURRENT_TIMESTAMP
               WHERE group_id=? AND status='waiting_user'""",
            (group_id,),
        )
        return max(0, cursor.rowcount)

    @staticmethod
    async def start_agent_run(task_id: str, role: RoleID) -> None:
        task = await TaskService.get_task(task_id)
        if not task or task.status != TaskStatus.IN_PROGRESS:
            raise ValueError("Agent run hanya boleh dimulai untuk task in_progress.")
        await db.execute(
            """INSERT INTO task_agent_runs
               (task_id, role_id, status, attempt_count, started_at, finished_at,
                response_text, error_text)
               VALUES (?, ?, 'running', 1, CURRENT_TIMESTAMP, NULL, NULL, NULL)
               ON CONFLICT(task_id, role_id) DO UPDATE SET
                   status='running',
                   attempt_count=task_agent_runs.attempt_count+1,
                   started_at=CURRENT_TIMESTAMP,
                   finished_at=NULL,
                   response_text=NULL,
                   error_text=NULL""",
            (task_id, role.value),
        )

    @staticmethod
    async def complete_agent_run(task_id: str, role: RoleID, response_text: str) -> bool:
        cursor = await db.execute(
            """UPDATE task_agent_runs
               SET status='succeeded', response_text=?, error_text=NULL,
                   finished_at=CURRENT_TIMESTAMP
               WHERE task_id=? AND role_id=? AND status='running'""",
            (response_text, task_id, role.value),
        )
        return cursor.rowcount == 1

    @staticmethod
    async def fail_agent_run(task_id: str, role: RoleID, error_text: str) -> bool:
        cursor = await db.execute(
            """UPDATE task_agent_runs
               SET status='failed', error_text=?, finished_at=CURRENT_TIMESTAMP
               WHERE task_id=? AND role_id=? AND status='running'""",
            (error_text[:1000], task_id, role.value),
        )
        return cursor.rowcount == 1

    @staticmethod
    async def cancel_agent_run(task_id: str, role: RoleID) -> None:
        await db.execute(
            """UPDATE task_agent_runs
               SET status='cancelled', finished_at=CURRENT_TIMESTAMP
               WHERE task_id=? AND role_id=? AND status='running'""",
            (task_id, role.value),
        )

    @staticmethod
    async def list_agent_runs(task_id: str) -> list[dict]:
        return await db.fetch_all(
            """SELECT task_id, role_id, status, attempt_count, response_text, error_text,
                      started_at, finished_at
               FROM task_agent_runs WHERE task_id=? ORDER BY started_at, role_id""",
            (task_id,),
        )

    @staticmethod
    async def record_failure(task_id: str) -> TaskStatus:
        async with db.transaction() as conn:
            cursor = await conn.execute(
                "SELECT retry_count, max_retries, status FROM tasks WHERE id=?",
                (task_id,),
            )
            raw = await cursor.fetchone()
            if not raw:
                raise ValueError(f"Task '{task_id}' tidak ditemukan")
            current = TaskStatus(raw["status"])
            if current in _TERMINAL_STATUSES:
                return current
            new_count = int(raw["retry_count"]) + 1
            max_retries = int(raw["max_retries"] or 3)
            new_status = TaskStatus.BLOCKED if new_count < max_retries else TaskStatus.FAILED
            await conn.execute(
                """UPDATE tasks
                   SET retry_count=?, status=?, updated_at=CURRENT_TIMESTAMP
                   WHERE id=? AND status=?""",
                (new_count, new_status.value, task_id, current.value),
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
            id=row["id"],
            group_id=row["group_id"],
            title=row["title"],
            description=row["description"] or "",
            current_owner=owner,
            status=TaskStatus(row["status"]),
            dependencies=deps,
            attempted_agents=attempted,
            retry_count=row["retry_count"],
            max_retries=row.get("max_retries", 3) or 3,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    async def list_task_history(group_id: str) -> list[TaskModel]:
        rows = await db.fetch_all(
            """SELECT id FROM tasks WHERE group_id=?
               AND status IN ('done','failed','cancelled')
               ORDER BY updated_at DESC, created_at DESC""",
            (group_id,),
        )
        result: list[TaskModel] = []
        for row in rows:
            task = await TaskService.get_task(row["id"])
            if task:
                result.append(task)
        return result

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
