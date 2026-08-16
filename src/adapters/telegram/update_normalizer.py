"""Telegram Message -> NormalizedMessage. Bot-originated messages are never re-ingested."""

from typing import Any

from src.adapters.telegram.bot_registry import bot_registry
from src.core.types import NormalizedMessage, RoleID


class TelegramUpdateNormalizer:
    @staticmethod
    def normalize_message(message: Any, received_by_role: RoleID) -> NormalizedMessage | None:
        from_user = getattr(message, "from_user", None)
        sender_id = str(from_user.id if from_user else "unknown")
        if bot_registry.is_self_bot_user_id(sender_id) or bool(getattr(from_user, "is_bot", False)):
            return None
        username = bot_registry.get_username(received_by_role)
        reply_to = getattr(message, "reply_to_message", None)
        reply_to_id = str(reply_to.message_id) if reply_to else None
        reply_from_user = getattr(reply_to, "from_user", None) if reply_to else None
        reply_to_role = (
            bot_registry.get_role_for_bot_user_id(str(reply_from_user.id))
            if reply_from_user and getattr(reply_from_user, "id", None) is not None
            else None
        )
        reply_text = None
        if reply_to:
            reply_text = (
                getattr(reply_to, "text", "")
                or getattr(reply_to, "caption", "")
                or ""
            ).strip() or None
        chat = getattr(message, "chat", None)
        text = getattr(message, "text", "") or getattr(message, "caption", "") or ""
        return NormalizedMessage(
            message_id=str(message.message_id),
            group_id=str(chat.id if chat else "unknown_chat"),
            sender_id=sender_id,
            sender_name=getattr(from_user, "full_name", "") if from_user else "",
            text=text,
            platform="telegram",
            reply_to_message_id=reply_to_id,
            reply_to_role=reply_to_role,
            reply_to_text=reply_text,
            received_by_bot_role=received_by_role,
            bot_identity=f"@{username}" if username else received_by_role.value,
        )
