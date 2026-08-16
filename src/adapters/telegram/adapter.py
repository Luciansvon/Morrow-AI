"""3 Telegram bots, one backend. Dedup is claimed before expensive attachment extraction."""

import asyncio
import io
from pathlib import Path
from typing import Any

from src.adapters.base import BaseChannelAdapter
from src.adapters.telegram.bot_registry import bot_registry
from src.adapters.telegram.sender import telegram_sender
from src.adapters.telegram.update_normalizer import TelegramUpdateNormalizer
from src.core.config import settings
from src.core.normalizer import MessageNormalizer
from src.core.types import AttachmentInfo, RoleID
from src.files.pipeline import attachment_pipeline
from src.storage.sqlite import db


class TelegramMultiBotAdapter(BaseChannelAdapter):
    def __init__(self):
        super().__init__()
        self._dispatchers: dict[RoleID, Any] = {}
        self._polling_tasks: list[asyncio.Task] = []
        self._running = False

    @staticmethod
    def _conversation_key(group_id: str, message_id: str) -> str:
        return f"telegram:{group_id}:{message_id}"

    async def _hydrate_conversation_context(self, message) -> None:
        """Restore parent thread/root context and persist the current user message."""
        parent = None
        if message.reply_to_message_id:
            parent = await db.fetch_one(
                """SELECT role_id, thread_id, task_id, root_user_text, response_text
                   FROM conversation_message_map
                   WHERE platform_message_id=? AND group_id=?""",
                (
                    self._conversation_key(message.group_id, message.reply_to_message_id),
                    message.group_id,
                ),
            )
        if parent:
            if message.reply_to_role is None and parent.get("role_id"):
                message.reply_to_role = RoleID(parent["role_id"])
            message.conversation_thread_id = parent.get("thread_id") or message.conversation_thread_id
            message.conversation_task_id = parent.get("task_id") or message.conversation_task_id
            message.conversation_root_text = parent.get("root_user_text") or message.conversation_root_text
            if not message.reply_to_text:
                message.reply_to_text = parent.get("response_text") or None

        message.conversation_thread_id = (
            message.conversation_thread_id or f"thr_{message.group_id}_{message.message_id}"
        )
        message.conversation_root_text = (
            message.conversation_root_text or (message.text or "").strip()
        )
        await db.execute(
            """INSERT OR REPLACE INTO conversation_message_map
               (platform_message_id, group_id, role_id, thread_id, task_id,
                root_user_text, response_text)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                self._conversation_key(message.group_id, message.message_id),
                message.group_id,
                message.reply_to_role.value if message.reply_to_role else None,
                message.conversation_thread_id,
                message.conversation_task_id,
                message.conversation_root_text,
                message.text,
            ),
        )

    async def _download_attachments(
        self,
        message: Any,
        bot: Any,
        group_id: str,
        platform_message_id: str,
        user_text: str = "",
        thread_id: str | None = None,
    ) -> list[AttachmentInfo]:
        items: list[tuple[Any, str, int | None]] = []
        document = getattr(message, "document", None)
        photos = getattr(message, "photo", None) or []
        if document:
            items.append((document, document.file_name or f"document_{document.file_unique_id}", getattr(document, "file_size", None)))
        elif photos:
            photo = photos[-1]
            items.append((photo, f"photo_{photo.file_unique_id}.jpg", getattr(photo, "file_size", None)))

        result: list[AttachmentInfo] = []
        max_bytes = settings.max_attachment_size_mb * 1024 * 1024
        for telegram_file, filename, reported_size in items:
            if reported_size and reported_size > max_bytes:
                result.append(AttachmentInfo(
                    file_id=str(getattr(telegram_file, "file_unique_id", "oversize")),
                    original_name=Path(filename).name,
                    detected_mime="application/octet-stream",
                    file_path="",
                    file_size=int(reported_size),
                    is_supported=False,
                    error_message=f"File melebihi batas {settings.max_attachment_size_mb} MB.",
                ))
                continue
            try:
                buffer = io.BytesIO()
                downloaded = await bot.download(telegram_file, destination=buffer)
                if hasattr(downloaded, "getvalue"):
                    content = downloaded.getvalue()
                else:
                    content = buffer.getvalue()
                result.append(
                    await attachment_pipeline.process_bytes(
                        filename,
                        content,
                        usage_context={
                            "group_id": group_id,
                            "thread_id": thread_id or f"thr_{group_id}_{platform_message_id}",
                        },
                        user_prompt=user_text,
                    )
                )
            except Exception as exc:
                result.append(AttachmentInfo(
                    file_id=str(getattr(telegram_file, "file_unique_id", "download_error")),
                    original_name=Path(filename).name,
                    detected_mime="application/octet-stream",
                    file_path="",
                    file_size=int(reported_size or 0),
                    is_supported=False,
                    error_message=f"Gagal mengunduh lampiran Telegram: {exc}",
                ))
        return result

    async def start(self) -> None:
        from aiogram import Dispatcher, types

        settings.validate_telegram_tokens()
        settings.validate_telegram_access()
        bot_registry.initialize_bots()
        await bot_registry.fetch_bot_identities()

        for role in (RoleID.MANAGER, RoleID.MARKETING, RoleID.ADVISOR):
            username = bot_registry.get_username(role)
            print(f"✅ {role.value.capitalize()} bot connected" + (f" (@{username})" if username else ""))
        print(f"✅ Allowed group loaded ({len(settings.allowlisted_groups)})")
        print(f"✅ Whitelist loaded ({len(settings.whitelisted_users)})")

        for role, bot in bot_registry.get_all_bots().items():
            dp = Dispatcher()

            def create_handler(current_role: RoleID, current_bot: Any):
                async def message_handler(message: types.Message):
                    if not self.message_handler:
                        return
                    norm = TelegramUpdateNormalizer.normalize_message(message, current_role)
                    if not norm:
                        return
                    allowed, _ = MessageNormalizer.check_access(norm)
                    if not allowed:
                        return
                    won = await MessageNormalizer.claim_event(norm.message_id, "telegram", norm.group_id)
                    if not won:
                        return
                    norm.event_claimed = True
                    await self._hydrate_conversation_context(norm)
                    norm.attachments = await self._download_attachments(
                        message,
                        current_bot,
                        norm.group_id,
                        norm.message_id,
                        norm.text,
                        norm.conversation_thread_id,
                    )
                    await self.message_handler(norm)
                return message_handler

            dp.message.register(create_handler(role, bot))
            self._dispatchers[role] = dp
            await bot.delete_webhook(drop_pending_updates=settings.telegram_drop_pending_updates)
            self._polling_tasks.append(asyncio.create_task(dp.start_polling(bot)))
        self._running = True
        print("🚀 Morrow ready - Menunggu pesan di grup Telegram...")

    def raise_if_unhealthy(self) -> None:
        if not self._running:
            return
        for task in self._polling_tasks:
            if not task.done():
                continue
            if task.cancelled():
                raise RuntimeError("Telegram polling task berhenti secara tak terduga.")
            exc = task.exception()
            if exc is not None:
                raise RuntimeError("Telegram polling task gagal.") from exc
            raise RuntimeError("Telegram polling task berhenti tanpa error saat adapter masih aktif.")

    async def stop(self) -> None:
        self._running = False
        for task in self._polling_tasks:
            task.cancel()
        if self._polling_tasks:
            await asyncio.gather(*self._polling_tasks, return_exceptions=True)
        for bot in bot_registry.get_all_bots().values():
            session = getattr(bot, "session", None)
            if session and hasattr(session, "close"):
                await session.close()
        self._polling_tasks.clear()
        self._dispatchers.clear()

    async def send_message(self, group_id: str, text: str, from_role: RoleID | None = None, reply_to_message_id: str | None = None) -> str:
        return await telegram_sender.send_message(group_id, text, from_role, reply_to_message_id)

    async def begin_activity(
        self,
        group_id: str,
        text: str,
        from_role: RoleID,
        reply_to_message_id: str | None = None,
    ) -> str | None:
        return await telegram_sender.send_activity(
            group_id,
            text,
            from_role,
            reply_to_message_id,
        )

    async def end_activity(
        self,
        group_id: str,
        activity_id: str | None,
        from_role: RoleID,
    ) -> None:
        await telegram_sender.delete_activity(group_id, activity_id, from_role)

    async def send_approval_prompt(self, group_id: str, approval_id: str, action_description: str, parameters: dict[str, Any]) -> None:
        await telegram_sender.send_approval_prompt(group_id, approval_id, action_description, parameters)
