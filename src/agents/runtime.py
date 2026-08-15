"""Runtime eksekusi agen mandiri dan perakitan konteks (Context Assembly)."""

from typing import Any

from src.core.types import ModalityType, NormalizedMessage, RiskLevel, RoleID, WorkloadType
from src.llm.model_policy import model_policy
from src.llm.openrouter import openrouter_client
from src.memory.service import memory_service
from src.skills.router import skill_router
from src.tasks.service import task_service


class AgentRuntime:
    """Runtime eksekusi independen per peran agen (CAP-AGENTS)."""

    def __init__(self, role: RoleID, base_prompt: str):
        self.role = role
        self.base_prompt = base_prompt

    async def assemble_context(
        self,
        message: NormalizedMessage,
        handoff_payload: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Merakit konteks agen (AC-019).
        Konteks HANYA berisi:
        1. Instruksi peran dasar
        2. Instruksi skill relevan
        3. Memori internal peran
        4. Memori bersama aktif
        5. Tugas aktif milik agen
        6. Payload handoff (jika ada)
        7. Pesan saat ini dan konten berkas terlampir
        DILARANG menyertakan seluruh riwayat obrolan mentah agen lain.
        """
        # 1. Ambil skill yang berhak digunakan peran
        skills = skill_router.resolve_skills_for_task(self.role, message)
        skills_text = "\n\n".join([f"### Skill: {s.name}\n{s.instructions}" for s in skills])

        # 2. Ambil memori peran dan memori bersama
        role_mem = await memory_service.get_role_memory(self.role)
        shared_mem = await memory_service.get_active_shared_memory()

        role_mem_str = "\n".join([f"- {k}: {v}" for k, v in role_mem.items()]) or "(Tidak ada)"
        shared_mem_str = "\n".join([f"- {k}: {v}" for k, v in shared_mem.items()]) or "(Tidak ada)"

        # 3. Ambil tugas aktif
        active_tasks = await task_service.list_active_tasks(message.group_id)
        my_tasks = [t for t in active_tasks if t.current_owner == self.role]
        tasks_str = "\n".join([f"- [{t.id}] {t.title} ({t.status.value})" for t in my_tasks]) or "(Tidak ada tugas aktif)"

        system_content = f"""{self.base_prompt}

## KEAHLIAN YANG TERSEDIA (SKILLS):
{skills_text}

## MEMORI INTERNAL PERAN ({self.role.value.upper()}):
{role_mem_str}

## MEMORI BERSAMA AKTIF (SHARED CONTEXT):
{shared_mem_str}

## TUGAS AKTIF SAYA:
{tasks_str}
"""
        if handoff_payload:
            system_content += f"\n## KONTEKS OPER ALIH (HANDOFF):\n{handoff_payload}"

        # 4. Susun pesan pengguna + lampiran
        user_content_parts = [message.text]
        for att in message.attachments:
            summary = f"\n[Lampiran Terverifikasi: {att.original_name} ({att.detected_mime})]"
            if att.extracted_text:
                summary += f"\nIsi Dokumen:\n{att.extracted_text}"
            if att.visual_description:
                summary += f"\nDeskripsi Visual: {att.visual_description}"
            user_content_parts.append(summary)

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": "\n".join(user_content_parts)},
        ]

    async def execute(
        self,
        message: NormalizedMessage,
        workload: WorkloadType = WorkloadType.ROUTINE,
        risk_level: RiskLevel = RiskLevel.LOW,
        handoff_payload: dict[str, Any] | None = None,
    ) -> str:
        """Mengeksekusi penalaran agen dan mengembalikan respon teks."""
        context_messages = await self.assemble_context(message, handoff_payload)
        modality = ModalityType.MULTIMODAL if any(att.detected_mime.startswith("image/") for att in message.attachments) else ModalityType.TEXT

        model_id, reasoning_effort = model_policy.resolve(
            role=self.role,
            workload=workload,
            risk_level=risk_level,
            modality=modality,
        )

        res = await openrouter_client.chat_completion(
            messages=context_messages,
            model=model_id,
            reasoning_effort=reasoning_effort,
        )
        return res.content
