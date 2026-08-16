"""Telegram sender. Never fabricates delivery success when a bot is unavailable."""

import logging
import re
from typing import Any

from src.adapters.telegram.bot_registry import bot_registry
from src.core.types import RoleID
from src.storage.sqlite import db

logger = logging.getLogger(__name__)


class TelegramSender:
    MAX_CHARS = 3900
    EMPTY_RESPONSE_FALLBACK = (
        "Saya belum berhasil menyusun respons yang bisa dikirim untuk pesan tadi. "
        "Input sudah diterima, tetapi hasil pemrosesan kosong."
    )
    _LIST_ITEM_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+\S")

    @staticmethod
    def _conversation_key(group_id: str, message_id: str) -> str:
        return f"telegram:{group_id}:{message_id}"

    @classmethod
    def _prepare_text(cls, text: str | None) -> str:
        """Keep plain-text output readable on narrow Telegram layouts and never empty."""
        raw = str(text or "").strip()
        if not raw:
            logger.warning("telegram_empty_response_guard activated")
            return cls.EMPTY_RESPONSE_FALLBACK

        output: list[str] = []
        in_code_block = False
        previous_was_list_item = False
        for raw_line in raw.splitlines():
            line = raw_line.rstrip()
            stripped = line.strip()
            if stripped.startswith("```"):
                output.append(line)
                in_code_block = not in_code_block
                previous_was_list_item = False
                continue

            is_list_item = bool(cls._LIST_ITEM_RE.match(line)) if not in_code_block else False
            if is_list_item and previous_was_list_item and output and output[-1] != "":
                output.append("")
            output.append(line)
            previous_was_list_item = is_list_item if stripped else False

        return "\n".join(output).strip() or cls.EMPTY_RESPONSE_FALLBACK

    @classmethod
    def _chunks(cls, text: str) -> list[str]:
        remaining = cls._prepare_text(text)
        chunks: list[str] = []
        while remaining:
            if len(remaining) <= cls.MAX_CHARS:
                chunks.append(remaining)
                break

            cut = cls.MAX_CHARS
            paragraph = remaining.rfind("\n\n", 0, cut)
            newline = remaining.rfind("\n", 0, cut)
            space = remaining.rfind(" ", 0, cut)
            if paragraph > cut // 3:
                cut = paragraph + 2
            elif newline > cut // 2:
                cut = newline + 1
            elif space > cut // 2:
                cut = space + 1

            chunk = remaining[:cut].rstrip()
            if chunk:
                chunks.append(chunk)
            remaining = remaining[cut:].lstrip("\n")
        return chunks or [cls.EMPTY_RESPONSE_FALLBACK]

    @staticmethod
    async def _send_one(bot: Any, group_id: str, text: str, reply_to: str | None):
        safe_text = TelegramSender._prepare_text(text)
        kwargs: dict[str, Any] = {"chat_id": int(group_id), "text": safe_text}
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
                        return await bot.send_message(chat_id=int(group_id), text=safe_text)
                    raise
            except Exception as exc:
                if "message to be replied not found" in str(exc).lower():
                    return await bot.send_message(chat_id=int(group_id), text=safe_text)
                raise
        return await bot.send_message(**kwargs)

    @classmethod
    async def _parent_conversation(cls, group_id: str, reply_to_message_id: str | None):
        if not reply_to_message_id:
            return None
        return await db.fetch_one(
            """SELECT thread_id, task_id, root_user_text
               FROM conversation_message_map
               WHERE platform_message_id=? AND group_id=?""",
            (cls._conversation_key(group_id, reply_to_message_id), group_id),
        )

    @classmethod
    async def _persist_sent_chunk(
        cls,
        group_id: str,
        role: RoleID,
        sent_id: str,
        chunk: str,
        parent: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if parent is None:
            return None
        try:
            await db.execute(
                """INSERT OR REPLACE INTO conversation_message_map
                   (platform_message_id, group_id, role_id, thread_id, task_id,
                    root_user_text, response_text)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    cls._conversation_key(group_id, sent_id),
                    group_id,
                    role.value,
                    parent.get("thread_id"),
                    parent.get("task_id"),
                    parent.get("root_user_text"),
                    chunk,
                ),
            )
            return parent
        except Exception as exc:
            # Delivery already succeeded. Continuity metadata is important but must not
            # turn a delivered Telegram answer into a false send failure.
            logger.warning("telegram_continuity_persist_failed error=%s", exc.__class__.__name__)
            return parent

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
        parent = await TelegramSender._parent_conversation(group_id, reply_to_message_id)
        for chunk in TelegramSender._chunks(text):
            sent = await TelegramSender._send_one(bot, group_id, chunk, reply_to)
            last_id = str(sent.message_id)
            await TelegramSender._persist_sent_chunk(group_id, role, last_id, chunk, parent)
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
