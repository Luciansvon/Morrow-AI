"""Adapter CLI interaktif & pengujian programmatic untuk Morrow."""

import uuid
from typing import Any

from src.adapters.base import BaseChannelAdapter
from src.core.types import NormalizedMessage, RoleID


class CLIAdapter(BaseChannelAdapter):
    """Adapter untuk terminal konsol dan simulasi pengujian otomatis."""

    def __init__(self):
        super().__init__()
        self.sent_messages: list[dict[str, Any]] = []
        self.pending_approvals: list[dict[str, Any]] = []
        self._running = False

    async def start(self) -> None:
        self._running = True

    async def stop(self) -> None:
        self._running = False

    async def send_message(
        self,
        group_id: str,
        text: str,
        from_role: RoleID | None = None,
        reply_to_message_id: str | None = None,
    ) -> str:
        msg_id = f"cli_msg_{uuid.uuid4().hex[:8]}"
        record = {
            "message_id": msg_id,
            "group_id": group_id,
            "text": text,
            "from_role": from_role.value if from_role else "system",
            "reply_to": reply_to_message_id,
        }
        self.sent_messages.append(record)
        role_label = f"[{from_role.value.upper()}]" if from_role else "[SISTEM]"
        print(f"\n{role_label}: {text}")
        return msg_id

    async def send_approval_prompt(
        self,
        group_id: str,
        approval_id: str,
        action_description: str,
        parameters: dict[str, Any],
    ) -> None:
        record = {
            "approval_id": approval_id,
            "group_id": group_id,
            "description": action_description,
            "parameters": parameters,
        }
        self.pending_approvals.append(record)
        print(f"\n⚠️ [PERSETUJUAN DIBUTUHKAN - ID: {approval_id}]")
        print(f"Aksi: {action_description}")
        print(f"Parameter: {parameters}")
        print(f"Ketik: /approve {approval_id} atau /reject {approval_id}")

    async def inject_message(self, message: NormalizedMessage) -> None:
        """Memasukkan pesan secara programmatik untuk pengujian."""
        if self.message_handler:
            await self.message_handler(message)
