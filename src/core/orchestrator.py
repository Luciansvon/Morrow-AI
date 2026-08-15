"""Orkestrator utama sistem Morrow v0.2 dengan concurrency lock per grup."""

import asyncio
from collections import defaultdict

from src.adapters.base import BaseChannelAdapter
from src.agents.advisor import advisor_agent
from src.agents.manager import manager_agent
from src.agents.marketing import marketing_agent
from src.core.normalizer import MessageNormalizer
from src.core.types import NormalizedMessage, RoleID
from src.memory.judge import memory_judge
from src.routing.role_router import role_router
from src.safety.conflict_detector import conflict_detector
from src.storage.sqlite import db
from src.tasks.service import task_service


class SystemOrchestrator:
    """Koordinator alur percakapan dan pengendali konkurensi grup (CAP-SAFETY / NFR-CON-002)."""

    def __init__(self, adapter: BaseChannelAdapter):
        self.adapter = adapter
        self.adapter.register_handler(self.handle_incoming_message)
        # Kunci konkurensi per-grup untuk mencegah blocking global antar grup yang berbeda
        self._group_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._agents = {
            RoleID.MANAGER: manager_agent,
            RoleID.MARKETING: marketing_agent,
            RoleID.ADVISOR: advisor_agent,
        }

    async def handle_incoming_message(self, message: NormalizedMessage) -> str | None:
        """Menangani pesan masuk dari adapter secara aman dan terurut."""
        # 1. Cek Akses Pengguna & Grup (AC-001)
        is_allowed, rejection_reason = MessageNormalizer.check_access(message)
        if not is_allowed:
            # Abaikan pesan tanpa membalas atau memproses jika tidak terdaftar (REQ-ACC-003)
            print(f"[Akses Ditolak] {rejection_reason}")
            return None

        # 2. Deduplikasi Event Masuk (AC-021)
        if await MessageNormalizer.is_duplicate_event(message.message_id):
            print(f"[Deduplikasi] Event {message.message_id} sudah diproses sebelumnya.")
            return None

        # 3. Kunci Konkurensi Per-Grup (AC-020)
        async with self._group_locks[message.group_id]:
            # 4. Deteksi Konflik Instruksi (AC-011, AC-015)
            active_tasks = await task_service.list_active_tasks(message.group_id)
            is_conflict, conflict_desc, affected_task = conflict_detector.detect_conflict(message.text, active_tasks)
            if is_conflict and affected_task:
                pause_msg = f"⚠️ **OTOMATISASI DIJEDA KARENA TERDETEKSI KONFLIK INSTRUKSI:**\n{conflict_desc}\n\nMohon konfirmasi klarifikasi manusia untuk melanjutkan."
                await self.adapter.send_message(message.group_id, pause_msg)
                return pause_msg

            # 5. Penyaluran Pesan ke Tepat Satu Agen Utama (AC-003, AC-004)
            primary_role, routing_reason = await role_router.route_message(message)
            agent_instance = self._agents[primary_role]

            # 6. Eksekusi Penalaran Agen
            response_text = await agent_instance.execute(message)

            # 7. Simpan Pesan dan Pemetaan Reply-Aware ke Database
            sent_msg_id = await self.adapter.send_message(
                group_id=message.group_id,
                text=response_text,
                from_role=primary_role,
                reply_to_message_id=message.message_id,
            )

            bot_id_str = f"bot_{primary_role.value}"
            await db.execute(
                """
                INSERT OR REPLACE INTO message_agent_map (platform_message_id, originating_role_id, bot_identity, group_id)
                VALUES (?, ?, ?, ?)
                """,
                (sent_msg_id, primary_role.value, bot_id_str, message.group_id),
            )

            # 8. Evaluasi Hakim Memori (Memory Judge) secara hemat di background
            await memory_judge.evaluate_and_commit(
                text=response_text,
                actor_id=message.sender_id,
                role_id=primary_role,
            )

            return response_text
