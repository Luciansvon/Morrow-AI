"""Penyalur pesan jalur cepat deterministik (Deterministic Fast Path)."""

import re

from src.core.types import NormalizedMessage, RoleID
from src.storage.sqlite import db


class FastPathRouter:
    """Penyalur pesan berbasis aturan cepat tanpa membuang biaya token LLM."""

    @staticmethod
    async def resolve_fast_path(message: NormalizedMessage) -> tuple[RoleID, str] | None:
        text_lower = message.text.lower().strip()

        # 1. Cek Sebutan Nama Eksplisit (@Manager, @Marketing, @Advisor, display name, atau username bot)
        from src.adapters.telegram.bot_registry import bot_registry

        # Ambil display name dinamis dari tabel agents
        rows = await db.fetch_all("SELECT role_id, display_name FROM agents")
        agent_names = {r["role_id"]: r["display_name"].lower() for r in rows}

        for role_id_str, disp_name in agent_names.items():
            role_enum = RoleID(role_id_str)
            bot_username = bot_registry.get_username(role_enum)

            patterns = [
                rf"@?{role_id_str}\b",
                rf"@?{re.escape(disp_name)}\b",
            ]
            if bot_username:
                patterns.append(rf"@{re.escape(bot_username)}\b")

            for pat in patterns:
                if re.search(pat, text_lower):
                    return role_enum, f"Sebutan eksplisit nama agen ({role_id_str})"

        # 2. Cek Reply-Aware Routing (AC-004)
        if message.reply_to_message_id:
            row = await db.fetch_one(
                "SELECT originating_role_id FROM message_agent_map WHERE platform_message_id = ?",
                (message.reply_to_message_id,),
            )
            if row and row["originating_role_id"]:
                return RoleID(row["originating_role_id"]), "Balasan pesan (Reply-Aware Mapping)"

        return None


fast_path_router = FastPathRouter()
