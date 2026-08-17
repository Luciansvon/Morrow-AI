"""Deterministic fast path: explicit role > reply > explicit task continuity."""

import re

from src.core.types import NormalizedMessage, RoleID
from src.routing.addressing import AddressingDetector
from src.storage.sqlite import db
from src.tasks.service import task_service


def message_map_key(group_id: str, platform_message_id: str, platform: str = "telegram") -> str:
    return f"{platform}:{group_id}:{platform_message_id}"


class FastPathRouter:
    @staticmethod
    async def resolve_fast_path(message: NormalizedMessage) -> tuple[RoleID, str] | None:
        text_lower = message.text.lower().strip()

        # Keep direct-address grammar identical to AddressingDetector. Bare role words that
        # are merely objects of a question must not become a routing instruction here.
        mentioned_roles = await AddressingDetector._explicit_roles(text_lower)
        if mentioned_roles:
            role = mentioned_roles[0]
            return role, f"Sebutan eksplisit direct address ({role.value})"

        if message.reply_to_role is not None:
            return message.reply_to_role, "Balasan langsung ke identitas bot Telegram"

        if message.reply_to_message_id:
            canonical = message_map_key(message.group_id, message.reply_to_message_id, message.platform)
            row = await db.fetch_one(
                "SELECT originating_role_id FROM message_agent_map WHERE platform_message_id=?",
                (canonical,),
            )
            if not row:
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
        if len(active_tasks) == 1 and re.search(
            r"\b(lanjut|lanjutkan|update|status|progres|progress|yang tadi)\b",
            text_lower,
        ):
            return active_tasks[0].current_owner, "Kontinuitas satu task aktif"
        return None


fast_path_router = FastPathRouter()
