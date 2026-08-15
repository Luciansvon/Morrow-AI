"""Antarmuka dasar BaseChannelAdapter untuk adapter pesan yang modular."""

from abc import ABC, abstractmethod
from collections.abc import Callable, Coroutine
from typing import Any

from src.core.types import NormalizedMessage, RoleID


class BaseChannelAdapter(ABC):
    """Antarmuka abstrak untuk jembatan platform perpesanan (Telegram, CLI, dsb)."""

    def __init__(self):
        self.message_handler: Callable[[NormalizedMessage], Coroutine[Any, Any, None]] | None = None

    def register_handler(self, handler: Callable[[NormalizedMessage], Coroutine[Any, Any, None]]) -> None:
        self.message_handler = handler

    @abstractmethod
    async def start(self) -> None:
        """Memulai listener adapter."""

    @abstractmethod
    async def stop(self) -> None:
        """Menghentikan listener adapter."""

    @abstractmethod
    async def send_message(
        self,
        group_id: str,
        text: str,
        from_role: RoleID | None = None,
        reply_to_message_id: str | None = None,
    ) -> str:
        """Mengirim pesan ke grup. Mengembalikan message_id platform yang dihasilkan."""

    @abstractmethod
    async def send_approval_prompt(
        self,
        group_id: str,
        approval_id: str,
        action_description: str,
        parameters: dict[str, Any],
    ) -> None:
        """Mengirim permintaan persetujuan aksi luar ke pengguna."""
