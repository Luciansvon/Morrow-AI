"""RoleID -> aiogram Bot registry."""

from typing import Any

from src.core.config import settings
from src.core.types import RoleID


class TelegramBotRegistry:
    def __init__(self):
        self._bots: dict[RoleID, Any] = {}
        self._bot_user_ids: set[str] = set()
        self._bot_user_roles: dict[str, RoleID] = {}
        self._bot_usernames: dict[RoleID, str] = {}
        self._initialized = False

    def initialize_bots(self, mock_bots: dict[RoleID, Any] | None = None) -> None:
        self._bots = {}
        self._bot_user_ids = set()
        self._bot_user_roles = {}
        self._bot_usernames = {}
        if mock_bots is not None:
            self._bots = dict(mock_bots)
            self._initialized = True
            return
        settings.validate_telegram_tokens()
        from aiogram import Bot
        for role, cfg in settings.telegram_bots.items():
            assert cfg.token is not None
            self._bots[role] = Bot(token=cfg.token.get_secret_value())
        self._initialized = True

    async def fetch_bot_identities(self) -> None:
        for role, bot in self._bots.items():
            me = await bot.get_me()
            user_id = str(me.id)
            self._bot_user_ids.add(user_id)
            self._bot_user_roles[user_id] = role
            if me.username:
                self._bot_usernames[role] = me.username.lower()

    def get_bot(self, role: RoleID) -> Any | None:
        return self._bots.get(role)

    def get_all_bots(self) -> dict[RoleID, Any]:
        return self._bots

    def is_self_bot_user_id(self, user_id: str) -> bool:
        return str(user_id) in self._bot_user_ids

    def register_bot_user_id(self, user_id: str, role: RoleID | None = None) -> None:
        normalized = str(user_id)
        self._bot_user_ids.add(normalized)
        if role is not None:
            self._bot_user_roles[normalized] = role

    def get_role_for_bot_user_id(self, user_id: str) -> RoleID | None:
        return self._bot_user_roles.get(str(user_id))

    def get_username(self, role: RoleID) -> str | None:
        return self._bot_usernames.get(role)

    def register_bot_username(self, role: RoleID, username: str) -> None:
        self._bot_usernames[role] = username.lower()


bot_registry = TelegramBotRegistry()
