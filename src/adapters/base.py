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

    async def begin_activity(
        self,
        group_id: str,
        text: str,
        from_role: RoleID,
        reply_to_message_id: str | None = None,
    ) -> str | None:
        """Tampilkan status kerja sementara bila channel mendukungnya."""
        return None

    async def end_activity(
        self,
        group_id: str,
        activity_id: str | None,
        from_role: RoleID,
    ) -> None:
        """Bersihkan status kerja sementara. Default no-op untuk adapter tanpa UI status."""
        return

    @abstractmethod
    async def send_approval_prompt(
        self,
        group_id: str,
        approval_id: str,
        action_description: str,
        parameters: dict[str, Any],
    ) -> None:
        """Mengirim permintaan persetujuan aksi luar ke pengguna."""
