"""Telegram sender. Never fabricates delivery success when a bot is unavailable."""

from typing import Any

from src.adapters.telegram.bot_registry import bot_registry
from src.core.types import RoleID


class TelegramSender:
    MAX_CHARS = 3900

    @staticmethod
    def _chunks(text: str) -> list[str]:
        if len(text) <= TelegramSender.MAX_CHARS:
            return [text]
        chunks: list[str] = []
        remaining = text
        while remaining:
            cut = min(len(remaining), TelegramSender.MAX_CHARS)
            if cut < len(remaining):
                newline = remaining.rfind("\n", 0, cut)
                if newline > cut // 2:
                    cut = newline + 1
            chunks.append(remaining[:cut])
            remaining = remaining[cut:]
        return chunks

    @staticmethod
    async def _send_one(bot: Any, group_id: str, text: str, reply_to: str | None):
        kwargs: dict[str, Any] = {"chat_id": int(group_id), "text": text}
        reply_num = int(reply_to) if reply_to and reply_to.lstrip("-").isdigit() else None
        if reply_num is not None:
            try:
                from aiogram.types import ReplyParameters

                kwargs["reply_parameters"] = ReplyParameters(message_id=reply_num)
                return await bot.send_message(**kwargs)
            except TypeError:
                kwargs.pop("reply_parameters", None)
                kwargs["reply_to_message_id"] = reply_num
                try:
                    return await bot.send_message(**kwargs)
                except Exception as exc:
                    if "message to be replied not found" in str(exc).lower():
                        return await bot.send_message(chat_id=int(group_id), text=text)
                    raise
            except Exception as exc:
                if "message to be replied not found" in str(exc).lower():
                    return await bot.send_message(chat_id=int(group_id), text=text)
                raise
        return await bot.send_message(**kwargs)

    @staticmethod
    async def send_message(
        group_id: str,
        text: str,
        from_role: RoleID | None = None,
        reply_to_message_id: str | None = None,
    ) -> str:
        role = from_role or RoleID.MANAGER
        bot = bot_registry.get_bot(role)
        if not bot or not hasattr(bot, "send_message"):
            raise RuntimeError(f"Telegram bot untuk role '{role.value}' belum siap.")

        last_id = ""
        reply_to = reply_to_message_id
        for chunk in TelegramSender._chunks(text):
            sent = await TelegramSender._send_one(bot, group_id, chunk, reply_to)
            last_id = str(sent.message_id)
            reply_to = last_id
        if not last_id:
            raise RuntimeError("Telegram tidak mengembalikan message_id setelah pengiriman.")
        return last_id

    @staticmethod
    async def send_activity(
        group_id: str,
        text: str,
        from_role: RoleID,
        reply_to_message_id: str | None = None,
    ) -> str | None:
        bot = bot_registry.get_bot(from_role)
        if not bot:
            return None
        try:
            if hasattr(bot, "send_chat_action"):
                await bot.send_chat_action(chat_id=int(group_id), action="typing")
        except Exception:
            pass
        try:
            return await TelegramSender.send_message(
                group_id,
                text,
                from_role,
                reply_to_message_id,
            )
        except Exception:
            return None

    @staticmethod
    async def delete_activity(group_id: str, activity_id: str | None, from_role: RoleID) -> None:
        if not activity_id or not str(activity_id).lstrip("-").isdigit():
            return
        bot = bot_registry.get_bot(from_role)
        if not bot or not hasattr(bot, "delete_message"):
            return
        try:
            await bot.delete_message(chat_id=int(group_id), message_id=int(activity_id))
        except Exception:
            # Activity UI must never make the actual answer fail.
            return

    @staticmethod
    async def send_approval_prompt(
        group_id: str,
        approval_id: str,
        action_description: str,
        parameters: dict[str, Any],
        requested_by_role: RoleID = RoleID.MANAGER,
    ) -> None:
        text = (
            "PERSETUJUAN TINDAKAN LUAR DIPERLUKAN\n\n"
            f"Agen: {requested_by_role.value.upper()}\n"
            f"Aksi: {action_description}\n"
            f"Parameter: {parameters}\n\n"
            f"Ketik /approve {approval_id} atau /reject {approval_id}"
        )
        await TelegramSender.send_message(group_id, text, requested_by_role)


telegram_sender = TelegramSender()
