"""Morrow orchestrator. Telegram is transport; all agent-to-agent collaboration is backend-controlled."""

import asyncio
import re
from collections import defaultdict
from typing import Any

from src.adapters.base import BaseChannelAdapter
from src.agents.advisor import advisor_agent
from src.agents.manager import manager_agent
from src.agents.marketing import marketing_agent
from src.approval.gateway import approval_gateway
from src.core.config import settings
from src.core.normalizer import MessageNormalizer
from src.core.types import (
    AddressingType,
    MessageIntent,
    NormalizedMessage,
    RiskLevel,
    RoleID,
    TaskStatus,
    WorkloadType,
)
from src.llm.usage_meter import usage_meter
from src.memory.judge import memory_judge
from src.persona.profiles import activity_text
from src.routing.addressing import addressing_detector
from src.routing.fast_path import message_map_key
from src.routing.intent import intent_detector
from src.routing.role_router import role_router
from src.routing.social import is_fast_social, social_response
from src.routing.task_analysis import task_analyzer
from src.safety.conflict_detector import conflict_detector
from src.safety.loop_guard import loop_guard
from src.storage.sqlite import db
from src.tasks.handoff import task_handoff
from src.tasks.service import task_service

APPROVAL_RE = re.compile(r"^/(approve|reject)(?:@\w+)?\s+(appr_[A-Za-z0-9_-]+)\s*$", re.IGNORECASE)


class SystemOrchestrator:
    def __init__(self, adapter: BaseChannelAdapter):
        self.adapter = adapter
        self.adapter.register_handler(self.handle_incoming_message)
        self._group_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._group_cancel_versions: dict[str, int] = defaultdict(int)
        self._agents = {
            RoleID.MANAGER: manager_agent,
            RoleID.MARKETING: marketing_agent,
            RoleID.ADVISOR: advisor_agent,
        }

    @staticmethod
    def _thread_id(message: NormalizedMessage) -> str:
        return message.conversation_thread_id or f"thr_{message.group_id}_{message.message_id}"

    def _cancel_version(self, group_id: str) -> int:
        return self._group_cancel_versions[group_id]

    def _was_cancelled(self, group_id: str, started_version: int) -> bool:
        return self._group_cancel_versions[group_id] != started_version

    async def _bind_conversation_task(
        self,
        message: NormalizedMessage,
        task_id: str,
        thread_id: str,
        sent_message_ids: list[str] | None = None,
    ) -> None:
        message.conversation_task_id = task_id
        message.conversation_thread_id = thread_id
        keys = [message_map_key(message.group_id, message.message_id, message.platform)]
        for sent_id in sent_message_ids or []:
            keys.append(message_map_key(message.group_id, sent_id, message.platform))
        for key in keys:
            await db.execute(
                """UPDATE conversation_message_map
                   SET task_id=?, thread_id=?
                   WHERE platform_message_id=? AND group_id=?""",
                (task_id, thread_id, key, message.group_id),
            )

    @staticmethod
    async def _task_is_cancelled(task_id: str) -> bool:
        current = await task_service.get_task(task_id)
        return bool(current and current.status == TaskStatus.CANCELLED)

    async def _map_sent_message(self, message: NormalizedMessage, sent_id: str, role: RoleID) -> None:
        key = message_map_key(message.group_id, sent_id, message.platform)
        await db.execute(
            """INSERT OR REPLACE INTO message_agent_map
               (platform_message_id, originating_role_id, bot_identity, group_id)
               VALUES (?, ?, ?, ?)""",
            (key, role.value, f"bot_{role.value}", message.group_id),
        )

    async def _send(
        self,
        message: NormalizedMessage,
        role: RoleID,
        text: str,
        reply_to: str | None = None,
    ) -> str:
        sent_id = await self.adapter.send_message(
            group_id=message.group_id,
            text=text,
            from_role=role,
            reply_to_message_id=reply_to or message.message_id,
        )
        await self._map_sent_message(message, sent_id, role)
        return sent_id

    async def _execute_agent(
        self,
        message: NormalizedMessage,
        role: RoleID,
        **kwargs: Any,
    ) -> str:
        activity_id: str | None = None
        begin_activity = getattr(self.adapter, "begin_activity", None)
        if callable(begin_activity):
            try:
                activity_id = await begin_activity(
                    group_id=message.group_id,
                    text=activity_text(role),
                    from_role=role,
                    reply_to_message_id=message.message_id,
                )
            except Exception:
                activity_id = None

        try:
            return await self._agents[role].execute(message, **kwargs)
        finally:
            end_activity = getattr(self.adapter, "end_activity", None)
            if callable(end_activity):
                try:
                    await end_activity(message.group_id, activity_id, role)
                except Exception:
                    pass

    async def _handle_approval_command(self, message: NormalizedMessage) -> str | None:
        match = APPROVAL_RE.match(message.text.strip())
        if not match:
            return None
        action, approval_id = match.groups()
        row = await approval_gateway.get_request(approval_id)
        if not row or row["group_id"] != message.group_id:
            text = "Approval tidak ditemukan untuk grup ini."
            await self._send(message, RoleID.MANAGER, text)
            return text
        requested_role = RoleID(row["requested_by_role"])
        if action.lower() == "reject":
            ok = await approval_gateway.reject_request(approval_id, message.group_id)
            text = "Permintaan tindakan ditolak." if ok else "Approval sudah tidak dapat ditolak."
            await self._send(message, requested_role, text)
            return text

        ok, reason = await approval_gateway.approve_request(
            approval_id=approval_id,
            approved_by=message.sender_id,
            expected_group_id=message.group_id,
        )
        if not ok:
            await self._send(message, requested_role, reason)
            return reason
        result = await approval_gateway.execute_approved_request(approval_id)
        if result.get("success"):
            text = f"Tindakan disetujui dan selesai. Execution ID: {result.get('execution_id')}"
        elif result.get("status") == "unknown" or result.get("approval_status") == "unknown":
            text = "Tindakan disetujui, tetapi hasil eksternalnya tidak pasti. Sistem tidak akan retry otomatis."
        else:
            text = f"Approval diterima, tetapi eksekusi gagal: {result.get('error', 'unknown error')}"
        await self._send(message, requested_role, text)
        return text

    async def _handle_control_command(self, message: NormalizedMessage) -> str | None:
        action = intent_detector.detect_control_command(message.text)
        if action is None:
            return None

        if action == "cancel":
            self._group_cancel_versions[message.group_id] += 1
            affected = await task_service.cancel_active_tasks(message.group_id)
            text = (
                f"Dihentikan. {affected} task aktif dibatalkan."
                if affected
                else "Dihentikan. Tidak ada task durable aktif; hasil pekerjaan yang masih berjalan tidak akan dikirim setelah sinyal stop ini."
            )
        elif action == "pause":
            self._group_cancel_versions[message.group_id] += 1
            affected = await task_service.pause_active_tasks(message.group_id)
            text = (
                f"Dijeda. {affected} task dipindahkan ke waiting_user."
                if affected
                else "Dijeda. Tidak ada task durable aktif; hasil pekerjaan yang masih berjalan tidak akan dikirim setelah sinyal pause ini."
            )
        else:
            affected = await task_service.resume_waiting_tasks(message.group_id)
            text = (
                f"{affected} task dibuka kembali ke status todo. Kirim instruksi lanjut atau reply task yang ingin diteruskan."
                if affected
                else "Tidak ada task waiting_user yang perlu dibuka kembali."
            )
        await self._send(message, RoleID.MANAGER, text)
        return text

    async def _run_collective_work(
        self,
        message: NormalizedMessage,
        targets: list[RoleID],
        coordinator: RoleID,
        cancel_version: int,
    ) -> str:
        unique_targets: list[RoleID] = []
        for role in [coordinator, *targets]:
            if role not in unique_targets:
                unique_targets.append(role)
        unique_targets = unique_targets[:3]

        task = await task_service.create_task(
            group_id=message.group_id,
            title=(message.text.strip() or "Kolaborasi tim")[:120],
            description=message.text,
            initial_owner=coordinator,
        )
        await task_service.update_task_status(task.id, TaskStatus.IN_PROGRESS)
        thread_id = self._thread_id(message)
        await self._bind_conversation_task(message, task.id, thread_id)
        analysis = task_analyzer.analyze(message.text, coordinator, len(message.attachments))
        contributions: list[tuple[RoleID, str]] = []
        failures: list[tuple[RoleID, str]] = []
        last_sent = message.message_id
        stop_reason: str | None = None
        synthesized = len(unique_targets) <= 1

        for role in unique_targets:
            if self._was_cancelled(message.group_id, cancel_version) or await self._task_is_cancelled(task.id):
                await task_service.cancel_agent_run(task.id, role)
                await task_service.update_task_status(task.id, TaskStatus.CANCELLED)
                return "Kolaborasi dihentikan oleh pengguna."
            if not await usage_meter.check_thread_budget(message.group_id, thread_id):
                stop_reason = "budget thread tercapai"
                break
            allowed, reason, _ = await loop_guard.can_continue_discussion(
                thread_id,
                message.group_id,
                role,
            )
            if not allowed:
                stop_reason = reason or "loop guard menghentikan diskusi"
                break

            if role == coordinator:
                work_msg = message
                handoff = {"mode": "discussion_coordinator", "task_id": task.id}
            else:
                context = "\n\n".join(
                    f"{contributor.value}: {text}" for contributor, text in contributions
                )
                work_msg = message.model_copy(
                    update={
                        "message_id": f"collab_{role.value}_{message.message_id}",
                        "text": (
                            f"Instruksi pengguna:\n{message.text}\n\n"
                            f"Kontribusi tim sejauh ini:\n{context}"
                        ),
                        "reply_to_message_id": last_sent,
                        "event_claimed": True,
                    }
                )
                handoff = {
                    "mode": "discussion_contributor",
                    "task_id": task.id,
                    "coordinator": coordinator.value,
                }

            await task_service.start_agent_run(task.id, role)
            try:
                response = await self._execute_agent(
                    work_msg,
                    role,
                    workload=analysis.workload,
                    risk_level=analysis.risk_level,
                    handoff_payload=handoff,
                    task_id=task.id,
                    thread_id=thread_id,
                )
                if self._was_cancelled(message.group_id, cancel_version) or await self._task_is_cancelled(task.id):
                    await task_service.cancel_agent_run(task.id, role)
                    await task_service.update_task_status(task.id, TaskStatus.CANCELLED)
                    return "Kolaborasi dihentikan oleh pengguna."
                last_sent = await self._send(message, role, response, last_sent)
                await task_service.complete_agent_run(task.id, role, response)
                contributions.append((role, response))
            except Exception as exc:
                error_text = f"{exc.__class__.__name__}: {exc}"
                await task_service.fail_agent_run(task.id, role, error_text)
                failures.append((role, error_text))
                continue

        all_targets_completed = len(contributions) == len(unique_targets) and not failures
        final_text = contributions[-1][1] if contributions else "Kolaborasi belum menghasilkan kontribusi."

        if failures:
            await task_service.update_task_status(task.id, TaskStatus.BLOCKED)
            failed_roles = ", ".join(role.value for role, _ in failures)
            notice = (
                "Kolaborasi belum lengkap. Agent yang gagal: "
                f"{failed_roles}. Agent lain tetap dijalankan; task ditandai blocked dan tidak dianggap selesai."
            )
            await self._send(message, coordinator, notice, last_sent)
            return notice

        if all_targets_completed and len(contributions) > 1:
            if not await usage_meter.check_thread_budget(message.group_id, thread_id):
                stop_reason = "budget thread tercapai sebelum sintesis"
            else:
                allowed, reason, _ = await loop_guard.can_continue_discussion(
                    thread_id,
                    message.group_id,
                    coordinator,
                )
                if not allowed:
                    stop_reason = reason or "loop guard menghentikan sintesis"
                else:
                    context = "\n\n".join(
                        f"{role.value.upper()}:\n{text}" for role, text in contributions
                    )
                    synth_msg = message.model_copy(
                        update={
                            "message_id": f"synthesis_{message.message_id}",
                            "text": (
                                f"Instruksi awal:\n{message.text}\n\n"
                                f"Kontribusi tim:\n{context}\n\n"
                                "Sintesis hasil akhir, hilangkan duplikasi dan nyatakan next action."
                            ),
                            "reply_to_message_id": last_sent,
                            "event_claimed": True,
                        }
                    )
                    try:
                        final_text = await self._execute_agent(
                            synth_msg,
                            coordinator,
                            workload=analysis.workload,
                            risk_level=analysis.risk_level,
                            handoff_payload={"mode": "final_synthesis", "task_id": task.id},
                            task_id=task.id,
                            thread_id=thread_id,
                        )
                        if self._was_cancelled(message.group_id, cancel_version) or await self._task_is_cancelled(task.id):
                            await task_service.update_task_status(task.id, TaskStatus.CANCELLED)
                            return "Kolaborasi dihentikan oleh pengguna."
                        await self._send(message, coordinator, final_text, last_sent)
                        synthesized = True
                    except Exception as exc:
                        stop_reason = f"sintesis gagal ({exc.__class__.__name__})"
                        await task_service.update_task_status(task.id, TaskStatus.BLOCKED)
                        notice = f"Kontribusi agent selesai, tetapi {stop_reason}. Task ditandai blocked."
                        await self._send(message, coordinator, notice, last_sent)
                        return notice

        complete = all_targets_completed and synthesized
        if complete:
            await task_service.update_task_status(task.id, TaskStatus.DONE)
            if await usage_meter.check_thread_budget(message.group_id, thread_id):
                try:
                    await memory_judge.evaluate_and_commit(
                        actor_id=message.sender_id,
                        role_id=coordinator,
                        group_id=message.group_id,
                        user_text=message.text,
                        assistant_text=final_text,
                        thread_id=thread_id,
                    )
                except Exception:
                    pass
            return final_text

        await task_service.update_task_status(task.id, TaskStatus.WAITING_USER)
        notice = "Kolaborasi dijeda sebelum hasil akhir lengkap" + (
            f": {stop_reason}." if stop_reason else "."
        )
        await self._send(message, coordinator, notice, last_sent)
        return notice

    async def _handle_locked_message(
        self,
        message: NormalizedMessage,
        cancel_version: int,
    ) -> str | None:
        approval_result = await self._handle_approval_command(message)
        if approval_result is not None:
            return approval_result

        addressing = await addressing_detector.detect(message)

        explicit_memory = memory_judge.parse_explicit_directive(message.text)
        if explicit_memory:
            memory_role = addressing.coordinator or (
                addressing.target_agents[0] if addressing.target_agents else RoleID.MANAGER
            )
            try:
                stored = await memory_judge.commit_explicit_directive(
                    message.text,
                    actor_id=message.sender_id,
                    role_id=memory_role,
                    group_id=message.group_id,
                )
            except Exception:
                stored = None
            if stored and stored.get("verified"):
                memory_type_labels = {
                    "decision": "keputusan",
                    "constraint": "batasan",
                    "fact": "fakta",
                    "status": "status",
                }
                label = memory_type_labels.get(stored["memory_type"], stored["memory_type"])
                text = f"Sudah dicatat ke memori bersama sebagai {label}: {stored['value']}"
            else:
                text = (
                    "Belum tersimpan. Backend tidak berhasil memverifikasi write memori, "
                    "jadi saya tidak akan mengklaim catatan itu sudah aman."
                )
            await self._send(message, memory_role, text)
            return text

        if addressing.intent == MessageIntent.SOCIAL:
            targets = addressing.target_agents or [RoleID.MANAGER]
            responses = []
            if is_fast_social(message.text):
                for role in targets:
                    text = social_response(role, message.text)
                    await self._send(message, role, text)
                    responses.append(f"[{role.value}]: {text}")
                return "\n".join(responses)

            thread_id = self._thread_id(message)
            for role in targets:
                text = await self._execute_agent(
                    message,
                    role,
                    workload=WorkloadType.CASUAL,
                    risk_level=RiskLevel.LOW,
                    thread_id=thread_id,
                )
                if self._was_cancelled(message.group_id, cancel_version):
                    return "Permintaan dihentikan oleh pengguna."
                await self._send(message, role, text)
                responses.append(f"[{role.value}]: {text}")
            return "\n".join(responses)

        active_tasks = await task_service.list_active_tasks(message.group_id)
        is_conflict, desc, affected = conflict_detector.detect_conflict(message.text, active_tasks)
        if is_conflict:
            if affected:
                await task_service.update_task_status(affected.id, TaskStatus.WAITING_USER)
                pause = f"Otomatisasi dijeda karena instruksi berpotensi konflik dengan task '{affected.title}'. {desc or ''} Mohon klarifikasi."
                await self._send(message, affected.current_owner, pause)
                return pause
            clarification = desc or (
                "Instruksi berpotensi konflik dengan beberapa task aktif. "
                "Sebutkan task yang dimaksud sebelum otomatisasi dilanjutkan."
            )
            await self._send(message, RoleID.MANAGER, clarification)
            return clarification

        if addressing.requires_coordinator and addressing.target_agents:
            return await self._run_collective_work(
                message,
                addressing.target_agents,
                addressing.coordinator or RoleID.MANAGER,
                cancel_version,
            )

        if addressing.addressing_type == AddressingType.SINGLE_AGENT and addressing.target_agents:
            primary_role = addressing.target_agents[0]
        else:
            primary_role, _ = await role_router.route_message(message)

        analysis = task_analyzer.analyze(message.text, primary_role, len(message.attachments))
        thread_id = self._thread_id(message)
        if len(analysis.collaborators) > 1:
            return await self._run_collective_work(
                message,
                [primary_role, *analysis.collaborators],
                primary_role,
                cancel_version,
            )

        if not await usage_meter.check_thread_budget(
            message.group_id,
            thread_id,
            limit=settings.budget_normal_task,
        ):
            notice = "Permintaan dijeda karena budget task sudah tercapai sebelum eksekusi agent."
            await self._send(message, primary_role, notice)
            return notice

        response = await self._execute_agent(
            message,
            primary_role,
            workload=analysis.workload,
            risk_level=analysis.risk_level,
            thread_id=thread_id,
        )
        if self._was_cancelled(message.group_id, cancel_version):
            return "Permintaan dihentikan oleh pengguna."
        sent_id = await self._send(message, primary_role, response)
        final_text = response
        final_role = primary_role

        if analysis.collaborators:
            target = analysis.collaborators[0]
            task = await task_service.create_task(
                group_id=message.group_id,
                title=(message.text.strip() or "Delegated work")[:120],
                description=message.text,
                initial_owner=primary_role,
            )
            await task_service.update_task_status(task.id, TaskStatus.IN_PROGRESS)
            await self._bind_conversation_task(message, task.id, thread_id, [sent_id])
            if self._was_cancelled(message.group_id, cancel_version):
                await task_service.update_task_status(task.id, TaskStatus.CANCELLED)
                return "Permintaan dihentikan oleh pengguna."
            ok, reason = await task_handoff.handoff_task(
                task_id=task.id,
                from_role=primary_role,
                to_role=target,
                reason=analysis.reason,
                context_payload={"initial_instruction": message.text},
            )
            if ok:
                delegated = message.model_copy(
                    update={
                        "message_id": f"handoff_{message.message_id}",
                        "text": (
                            f"Instruksi awal pengguna:\n{message.text}\n\n"
                            f"Respons awal {primary_role.value}:\n{response}"
                        ),
                        "reply_to_message_id": sent_id,
                        "event_claimed": True,
                    }
                )
                try:
                    final_text = await self._execute_agent(
                        delegated,
                        target,
                        workload=analysis.workload,
                        risk_level=analysis.risk_level,
                        handoff_payload={
                            "from_role": primary_role.value,
                            "task_id": task.id,
                        },
                        task_id=task.id,
                        thread_id=thread_id,
                    )
                    if self._was_cancelled(message.group_id, cancel_version) or await self._task_is_cancelled(task.id):
                        await task_service.update_task_status(task.id, TaskStatus.CANCELLED)
                        return "Permintaan dihentikan oleh pengguna."
                    final_sent_id = await self._send(message, target, final_text, sent_id)
                    await self._bind_conversation_task(message, task.id, thread_id, [sent_id, final_sent_id])
                except Exception:
                    await task_service.update_task_status(task.id, TaskStatus.BLOCKED)
                    raise
                final_role = target
                await task_service.update_task_status(task.id, TaskStatus.DONE)
            else:
                await task_service.update_task_status(task.id, TaskStatus.BLOCKED)
                final_text = response + f"\n\nHandoff tidak dijalankan: {reason}"

        if self._was_cancelled(message.group_id, cancel_version):
            return "Permintaan dihentikan oleh pengguna."
        if await usage_meter.check_thread_budget(
            message.group_id,
            thread_id,
            limit=settings.budget_normal_task,
        ):
            await memory_judge.evaluate_and_commit(
                actor_id=message.sender_id,
                role_id=final_role,
                group_id=message.group_id,
                user_text=message.text,
                assistant_text=final_text,
                thread_id=thread_id,
            )
        return final_text

    async def handle_incoming_message(self, message: NormalizedMessage) -> str | None:
        allowed, _ = MessageNormalizer.check_access(message)
        if not allowed:
            return None

        claimed_here = False
        if not message.event_claimed:
            won = await MessageNormalizer.claim_event(
                message.message_id,
                message.platform,
                message.group_id,
            )
            if not won:
                return None
            message.event_claimed = True
            claimed_here = True

        try:
            control_result = await self._handle_control_command(message)
            if control_result is not None:
                result = control_result
            else:
                cancel_version = self._cancel_version(message.group_id)
                async with self._group_locks[message.group_id]:
                    result = await self._handle_locked_message(message, cancel_version)
        except Exception as exc:
            if claimed_here:
                await MessageNormalizer.mark_event_failed(
                    message.message_id,
                    message.platform,
                    message.group_id,
                    error=f"{exc.__class__.__name__}: {exc}",
                )
            raise
        else:
            if claimed_here:
                await MessageNormalizer.mark_event_completed(
                    message.message_id,
                    message.platform,
                    message.group_id,
                )
            return result
