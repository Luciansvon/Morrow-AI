"""Deterministic fast path: explicit role > reply > explicit task continuity."""

import re

from src.core.types import NormalizedMessage, RoleID
from src.storage.sqlite import db
from src.tasks.service import task_service


def message_map_key(group_id: str, platform_message_id: str, platform: str = "telegram") -> str:
    return f"{platform}:{group_id}:{platform_message_id}"


class FastPathRouter:
    @staticmethod
    async def resolve_fast_path(message: NormalizedMessage) -> tuple[RoleID, str] | None:
        text_lower = message.text.lower().strip()
        from src.adapters.telegram.bot_registry import bot_registry

        rows = await db.fetch_all("SELECT role_id, display_name FROM agents")
        agent_names = {r["role_id"]: r["display_name"].lower() for r in rows}
        # Decision OQ-001: explicit address wins over reply context.
        for role_id_str, display_name in agent_names.items():
            role = RoleID(role_id_str)
            username = bot_registry.get_username(role)
            patterns = [rf"@?{re.escape(role_id_str)}\b", rf"@?{re.escape(display_name)}\b"]
            if username:
                patterns.append(rf"@{re.escape(username)}\b")
            if any(re.search(pattern, text_lower) for pattern in patterns):
                return role, f"Sebutan eksplisit nama agen ({role_id_str})"

        if message.reply_to_message_id:
            canonical = message_map_key(message.group_id, message.reply_to_message_id, message.platform)
            row = await db.fetch_one(
                "SELECT originating_role_id FROM message_agent_map WHERE platform_message_id=?",
                (canonical,),
            )
            if not row:  # compatibility data/test lama
                row = await db.fetch_one(
                    "SELECT originating_role_id FROM message_agent_map WHERE platform_message_id=? AND group_id=?",
                    (message.reply_to_message_id, message.group_id),
                )
            if row and row.get("originating_role_id"):
                return RoleID(row["originating_role_id"]), "Balasan pesan (Reply-Aware Mapping)"

        active_tasks = await task_service.list_active_tasks(message.group_id)
        for task in active_tasks:
            if task.id.lower() in text_lower:
                return task.current_owner, f"Task ID aktif {task.id}"
        if len(active_tasks) == 1 and re.search(r"\b(lanjut|lanjutkan|update|status|progres|progress|yang tadi)\b", text_lower):
            return active_tasks[0].current_owner, "Kontinuitas satu task aktif"
        return None


fast_path_router = FastPathRouter()
