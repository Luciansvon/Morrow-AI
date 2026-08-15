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
            # 4. Deteksi Pengalamatan Kolektif & Niat Pesan (Addressing & Intent)
            from src.core.types import AddressingType, MessageIntent
            from src.routing.addressing import addressing_detector

            addr_res = await addressing_detector.detect(message)

            # MODE A: SOCIAL BROADCAST (contoh: "halo semua", "pagi tim", "Manager dan Marketing, halo")
            if addr_res.allow_multi_response and addr_res.intent == MessageIntent.SOCIAL:
                responses = []
                for role in addr_res.target_agents:
                    agent = self._agents[role]
                    resp = await agent.execute(message)
                    sent_id = await self.adapter.send_message(
                        group_id=message.group_id,
                        text=resp,
                        from_role=role,
                        reply_to_message_id=message.message_id,
                    )
                    await db.execute(
                        """
                        INSERT OR REPLACE INTO message_agent_map (platform_message_id, originating_role_id, bot_identity, group_id)
                        VALUES (?, ?, ?, ?)
                        """,
                        (sent_id, role.value, f"bot_{role.value}", message.group_id),
                    )
                    responses.append(f"[{role.value.capitalize()}]: {resp}")
                # Sapaan sosial selesai (tanpa membuat task dan tanpa mencemari memori durable)
                return "\n".join(responses)

            # MODE B: MULTI-AGENT WORK REQUEST (contoh: "semua, bantu strategi launch", "Manager dan Advisor, evaluasi keputusan ini")
            if addr_res.requires_coordinator and addr_res.target_agents:
                coordinator_role = addr_res.coordinator or RoleID.MANAGER
                coord_agent = self._agents[coordinator_role]
                coord_resp = await coord_agent.execute(message)
                coord_msg_id = await self.adapter.send_message(
                    group_id=message.group_id,
                    text=coord_resp,
                    from_role=coordinator_role,
                    reply_to_message_id=message.message_id,
                )
                await db.execute(
                    """
                    INSERT OR REPLACE INTO message_agent_map (platform_message_id, originating_role_id, bot_identity, group_id)
                    VALUES (?, ?, ?, ?)
                    """,
                    (coord_msg_id, coordinator_role.value, f"bot_{coordinator_role.value}", message.group_id),
                )

                # Kontribusi dari agen spesialis lain yang ditargetkan
                for other_role in addr_res.target_agents:
                    if other_role != coordinator_role:
                        other_agent = self._agents[other_role]
                        other_msg = NormalizedMessage(
                            message_id=f"collab_{other_role.value}_{message.message_id}",
                            group_id=message.group_id,
                            sender_id=message.sender_id,
                            sender_name=message.sender_name,
                            text=f"[Kolaborasi Tim]: {coord_resp}\n\nInstruksi pengguna: {message.text}",
                            reply_to_message_id=coord_msg_id,
                        )
                        other_resp = await other_agent.execute(other_msg)
                        other_msg_id = await self.adapter.send_message(
                            group_id=message.group_id,
                            text=other_resp,
                            from_role=other_role,
                            reply_to_message_id=coord_msg_id,
                        )
                        await db.execute(
                            """
                            INSERT OR REPLACE INTO message_agent_map (platform_message_id, originating_role_id, bot_identity, group_id)
                            VALUES (?, ?, ?, ?)
                            """,
                            (other_msg_id, other_role.value, f"bot_{other_role.value}", message.group_id),
                        )
                return coord_resp

            # MODE C: OBJECT QUANTIFIER / SINGLE AGENT / NORMAL TASK
            # Deteksi Konflik Instruksi (AC-011, AC-015)
            active_tasks = await task_service.list_active_tasks(message.group_id)
            is_conflict, conflict_desc, affected_task = conflict_detector.detect_conflict(message.text, active_tasks)
            if is_conflict and affected_task:
                pause_msg = f"⚠️ **OTOMATISASI DIJEDA KARENA TERDETEKSI KONFLIK INSTRUKSI:**\n{conflict_desc}\n\nMohon konfirmasi klarifikasi manusia untuk melanjutkan."
                await self.adapter.send_message(message.group_id, pause_msg)
                return pause_msg

            # Penyaluran Pesan ke Tepat Satu Agen Utama (AC-003, AC-004)
            if addr_res.addressing_type == AddressingType.SINGLE_AGENT and addr_res.target_agents:
                primary_role = addr_res.target_agents[0]
            else:
                primary_role, routing_reason = await role_router.route_message(message)

            agent_instance = self._agents[primary_role]
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

            # 9. Koordinasi Antar-Agen Backend Terkendali (Backend-Controlled Delegation)
            delegation_target = None
            lower_resp = response_text.lower()
            if addr_res.intent != MessageIntent.SOCIAL:
                if primary_role == RoleID.MANAGER:
                    if any(kw in lower_resp for kw in ["delegasikan ke marketing", "serahkan ke marketing", "tindak lanjut marketing", "saya delegasikan ke @marketing"]):
                        delegation_target = RoleID.MARKETING
                    elif any(kw in lower_resp for kw in ["delegasikan ke advisor", "serahkan ke advisor", "tindak lanjut advisor", "saya delegasikan ke @advisor"]):
                        delegation_target = RoleID.ADVISOR
                elif primary_role == RoleID.MARKETING:
                    if any(kw in lower_resp for kw in ["delegasikan ke advisor", "konsultasikan ke advisor", "saya delegasikan ke @advisor"]):
                        delegation_target = RoleID.ADVISOR

            if delegation_target and delegation_target != primary_role:
                from src.tasks.handoff import task_handoff
                new_task = await task_service.create_task(
                    group_id=message.group_id,
                    title=f"Delegasi dari {primary_role.value.capitalize()}",
                    description=message.text,
                    initial_owner=primary_role,
                )
                await task_handoff.handoff_task(
                    task_id=new_task.id,
                    from_role=primary_role,
                    to_role=delegation_target,
                    reason=f"Delegasi otomatis dari {primary_role.value}",
                )

                delegated_agent = self._agents[delegation_target]
                handoff_msg = NormalizedMessage(
                    message_id=f"handoff_{message.message_id}",
                    group_id=message.group_id,
                    sender_id=message.sender_id,
                    sender_name=message.sender_name,
                    text=f"[Pesan dari {primary_role.value.capitalize()}]: {response_text}\n\nInstruksi awal: {message.text}",
                    reply_to_message_id=sent_msg_id,
                )
                delegated_response = await delegated_agent.execute(
                    handoff_msg,
                    handoff_payload={"from_role": primary_role.value, "task_id": new_task.id, "initial_instruction": message.text},
                )

                delegated_msg_id = await self.adapter.send_message(
                    group_id=message.group_id,
                    text=delegated_response,
                    from_role=delegation_target,
                    reply_to_message_id=sent_msg_id,
                )
                bot_id_str = f"bot_{delegation_target.value}"
                await db.execute(
                    """
                    INSERT OR REPLACE INTO message_agent_map (platform_message_id, originating_role_id, bot_identity, group_id)
                    VALUES (?, ?, ?, ?)
                    """,
                    (delegated_msg_id, delegation_target.value, bot_id_str, message.group_id),
                )

            return response_text
