"""Adapter Multi-Bot Telegram terpadu untuk sistem Morrow v0.2."""

import asyncio
from typing import Any

from src.adapters.base import BaseChannelAdapter
from src.adapters.telegram.bot_registry import bot_registry
from src.adapters.telegram.sender import telegram_sender
from src.adapters.telegram.update_normalizer import TelegramUpdateNormalizer
from src.core.types import RoleID


class TelegramMultiBotAdapter(BaseChannelAdapter):
    """Adapter perpesanan Telegram yang mengelola 3 Bot independen pada 1 runtime."""

    def __init__(self):
        super().__init__()
        self._dispatchers = {}
        self._polling_tasks = []
        self._running = False

    async def start(self) -> None:
        """Memulai runtime 3 bot Telegram dalam satu event loop."""
        try:
            from aiogram import Dispatcher, types

            bot_registry.initialize_bots()
            await bot_registry.fetch_bot_identities()

            for role, bot in bot_registry.get_all_bots().items():
                dp = Dispatcher()

                # Handler pesan masuk per bot
                def create_handler(current_role: RoleID):
                    async def message_handler(message: types.Message):
                        if not self.message_handler:
                            return

                        norm_msg = TelegramUpdateNormalizer.normalize_message(
                            message=message,
                            received_by_role=current_role,
                        )
                        if norm_msg:
                            await self.message_handler(norm_msg)

                    return message_handler

                dp.message.register(create_handler(role))
                self._dispatchers[role] = dp

                # Jalankan polling per bot
                task = asyncio.create_task(dp.start_polling(bot))
                self._polling_tasks.append(task)

            self._running = True
        except Exception as e:
            print(f"Peringatan: Gagal menjalankan Telegram Polling ({e}).")

    async def stop(self) -> None:
        """Menghentikan seluruh polling dan menutup sesi koneksi 3 bot."""
        self._running = False
        for task in self._polling_tasks:
            task.cancel()

        for bot in bot_registry.get_all_bots().values():
            if hasattr(bot, "session") and hasattr(bot.session, "close"):
                await bot.session.close()

    async def send_message(
        self,
        group_id: str,
        text: str,
        from_role: RoleID | None = None,
        reply_to_message_id: str | None = None,
    ) -> str:
        return await telegram_sender.send_message(
            group_id=group_id,
            text=text,
            from_role=from_role,
            reply_to_message_id=reply_to_message_id,
        )

    async def send_approval_prompt(
        self,
        group_id: str,
        approval_id: str,
        action_description: str,
        parameters: dict[str, Any],
    ) -> None:
        await telegram_sender.send_approval_prompt(
            group_id=group_id,
            approval_id=approval_id,
            action_description=action_description,
            parameters=parameters,
            requested_by_role=RoleID.MANAGER,
        )
