"""Hakim Memori (Memory Judge) menggunakan MiMo-V2.5 Non-Thinking."""

import json
from typing import Any

from src.core.types import MemoryScope, MemoryType, RoleID
from src.llm.model_catalog import MODEL_CATALOG
from src.llm.openrouter import openrouter_client
from src.memory.service import memory_service

JUDGE_SYSTEM_PROMPT = """Anda adalah Hakim Memori (Memory Judge) untuk sistem AI Morrow.
Tugas Anda adalah memeriksa pesan agen/pengguna untuk menentukan apakah ada fakta resmi, tenggat waktu (deadline), atau keputusan proyek yang layak disimpan ke memori permanen.

Format Output WAJIB JSON:
{
  "should_store": true | false,
  "scope": "shared" | "role",
  "key": "nama_kunci_singkat",
  "value": "nilai_fakta_atau_keputusan",
  "memory_type": "decision" | "fact" | "constraint" | "status",
  "reason": "alasan_penyimpanan"
}
"""


class MemoryJudge:
    """Penyaring fakta berharga agar memori bersama tidak tercemar obrolan sampah."""

    @staticmethod
    async def evaluate_and_commit(
        text: str,
        actor_id: str,
        role_id: RoleID | None = None,
    ) -> dict[str, Any] | None:
        messages = [
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": f"Evaluasi teks berikut:\n\n{text}"},
        ]
        try:
            res = await openrouter_client.chat_completion(
                messages=messages,
                model=MODEL_CATALOG["mimo_v2_5"].model_id,
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            data = json.loads(res.content)
            if data.get("should_store") and data.get("key") and data.get("value"):
                scope_enum = MemoryScope.SHARED if data.get("scope") == "shared" else MemoryScope.ROLE
                mem_type = MemoryType(data.get("memory_type", "fact"))
                await memory_service.set_memory(
                    scope=scope_enum,
                    key=data["key"],
                    value=data["value"],
                    changed_by_actor=actor_id,
                    role_id=role_id if scope_enum == MemoryScope.ROLE else None,
                    changed_by_role=role_id,
                    reason=data.get("reason", "Disimpan oleh Memory Judge"),
                    memory_type=mem_type,
                )
                return data
        except Exception:
            pass
        return None


memory_judge = MemoryJudge()
