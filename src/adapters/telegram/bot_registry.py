"""Registri Bot Telegram untuk memetakan RoleID ke instance Bot aiogram."""

from typing import Any

from src.core.config import settings
from src.core.types import RoleID


class TelegramBotRegistry:
    """Manajer registri 3 instance Bot Telegram independen pada 1 runtime Morrow."""

    def __init__(self):
        self._bots: dict[RoleID, Any] = {}
        self._bot_user_ids: set[str] = set()
        self._bot_usernames: dict[RoleID, str] = {}
        self._initialized = False

    def initialize_bots(self, mock_bots: dict[RoleID, Any] | None = None) -> None:
        """
        Menginisialisasi instance Bot dari konfigurasi.
        Jika mock_bots diberikan (untuk unit test), gunakan mock tersebut.
        """
        if mock_bots:
            self._bots = mock_bots
            self._initialized = True
            return

        settings.validate_telegram_tokens()

        try:
            from aiogram import Bot

            for role, bot_cfg in settings.telegram_bots.items():
                if bot_cfg.token:
                    # Ambil secret value dengan aman
                    token_val = bot_cfg.token.get_secret_value()
                    bot_instance = Bot(token=token_val)
                    self._bots[role] = bot_instance

            self._initialized = True
        except ImportError:
            pass

    async def fetch_bot_identities(self) -> None:
        """Mengambil info identitas (ID & Username) dari server Telegram untuk filter self-echo."""
        for role, bot in self._bots.items():
            if hasattr(bot, "get_me"):
                try:
                    me = await bot.get_me()
                    self._bot_user_ids.add(str(me.id))
                    if me.username:
                        self._bot_usernames[role] = me.username.lower()
                except Exception:
                    pass

    def get_bot(self, role: RoleID) -> Any | None:
        return self._bots.get(role)

    def get_all_bots(self) -> dict[RoleID, Any]:
        return self._bots

    def is_self_bot_user_id(self, user_id: str) -> bool:
        """Memeriksa apakah pengirim adalah salah satu dari bot Morrow sendiri."""
        return str(user_id) in self._bot_user_ids

    def register_bot_user_id(self, user_id: str) -> None:
        self._bot_user_ids.add(str(user_id))

    def get_username(self, role: RoleID) -> str | None:
        return self._bot_usernames.get(role)

    def register_bot_username(self, role: RoleID, username: str) -> None:
        self._bot_usernames[role] = username.lower()


bot_registry = TelegramBotRegistry()
