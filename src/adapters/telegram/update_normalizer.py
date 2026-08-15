"""Normalisasi update perpesanan Telegram dan penyaringan pesan bot sendiri."""

from typing import Any

from src.adapters.telegram.bot_registry import bot_registry
from src.core.types import NormalizedMessage, RoleID


class TelegramUpdateNormalizer:
    """Normalizer pesan Telegram ke skema NormalizedMessage."""

    @staticmethod
    def normalize_message(message: Any, received_by_role: RoleID) -> NormalizedMessage | None:
        """
        Mengubah payload aiogram Message menjadi NormalizedMessage.
        Mengembalikan None jika pesan berasal dari salah satu bot Morrow sendiri (Anti-Loop Self-Echo).
        """
        sender_id = str(message.from_user.id if message.from_user else "unknown")

        # 1. Saring jika pesan dikirim oleh bot Morrow sendiri
        if bot_registry.is_self_bot_user_id(sender_id):
            return None

        # 2. Ambil username bot penerima jika ada
        bot_username = bot_registry.get_username(received_by_role)
        bot_identity = f"@{bot_username}" if bot_username else received_by_role.value

        reply_to_id = None
        if getattr(message, "reply_to_message", None):
            reply_to_id = str(message.reply_to_message.message_id)

        chat_id = str(message.chat.id if hasattr(message, "chat") else "unknown_chat")
        text_content = getattr(message, "text", "") or getattr(message, "caption", "") or ""

        return NormalizedMessage(
            message_id=str(message.message_id),
            group_id=chat_id,
            sender_id=sender_id,
            sender_name=message.from_user.full_name if message.from_user else "",
            text=text_content,
            reply_to_message_id=reply_to_id,
            received_by_bot_role=received_by_role,
            bot_identity=bot_identity,
        )
