"""Pengirim pesan ke grup Telegram menggunakan instance Bot yang sesuai dengan RoleID."""

import uuid
from typing import Any

from src.adapters.telegram.bot_registry import bot_registry
from src.core.types import RoleID


class TelegramSender:
    """Komponen pengiriman pesan resmi menggunakan identitas bot masing-masing peran."""

    @staticmethod
    async def send_message(
        group_id: str,
        text: str,
        from_role: RoleID | None = None,
        reply_to_message_id: str | None = None,
    ) -> str:
        target_role = from_role or RoleID.MANAGER
        bot = bot_registry.get_bot(target_role)

        # Jika bot belum aktif / dalam lingkungan simulasi
        if not bot or not hasattr(bot, "send_message"):
            dummy_id = f"tg_msg_{target_role.value}_{uuid.uuid4().hex[:6]}"
            return dummy_id

        reply_id = int(reply_to_message_id) if reply_to_message_id and reply_to_message_id.isdigit() else None
        sent = await bot.send_message(
            chat_id=int(group_id),
            text=text,
            reply_to_message_id=reply_id,
            parse_mode="Markdown",
        )
        return str(sent.message_id)

    @staticmethod
    async def send_approval_prompt(
        group_id: str,
        approval_id: str,
        action_description: str,
        parameters: dict[str, Any],
        requested_by_role: RoleID = RoleID.MANAGER,
    ) -> None:
        bot = bot_registry.get_bot(requested_by_role)
        if not bot or not hasattr(bot, "send_message"):
            return

        text = (
            f"⚠️ **PERSETUJUAN TINDAKAN LUAR DIPERLUKAN**\n\n"
            f"**Agen Pemohon:** `{requested_by_role.value.upper()}`\n"
            f"**Aksi:** {action_description}\n"
            f"**Parameter:** `{parameters}`\n\n"
            f"Ketik `/approve {approval_id}` untuk setuju atau `/reject {approval_id}` untuk tolak."
        )
        await bot.send_message(chat_id=int(group_id), text=text, parse_mode="Markdown")


telegram_sender = TelegramSender()
