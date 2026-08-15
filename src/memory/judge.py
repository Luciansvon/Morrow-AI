"""Memory Judge menyimpan fakta/keputusan eksplisit dari exchange, bukan spekulasi agent."""

import json
from typing import Any

from src.core.config import settings
from src.core.types import MemoryScope, MemoryType, RoleID
from src.llm.model_catalog import MODEL_CATALOG
from src.llm.openrouter import openrouter_client
from src.memory.service import memory_service

JUDGE_SYSTEM_PROMPT = """Anda adalah Hakim Memori (Memory Judge) Morrow.
Simpan hanya informasi durable yang benar-benar dinyatakan/ditetapkan pengguna atau hasil status sistem yang terverifikasi: fakta proyek, keputusan final, constraint, deadline, atau status penting.
JANGAN simpan sapaan, brainstorming sementara, opini/saran agent, asumsi, atau fakta yang hanya dibuat oleh jawaban assistant.
Jika assistant menyebut sesuatu yang tidak didukung pesan pengguna, jangan simpan sebagai fakta.
Output JSON ketat:
{"should_store": true|false, "items": [{"scope":"shared"|"role","key":"...","value":"...","memory_type":"decision"|"fact"|"constraint"|"status","reason":"..."}]}
"""


class MemoryJudge:
    @staticmethod
    async def evaluate_and_commit(
        text: str | None = None,
        actor_id: str = "system",
        role_id: RoleID | None = None,
        group_id: str = "__global__",
        user_text: str | None = None,
        assistant_text: str | None = None,
        thread_id: str | None = None,
    ) -> dict[str, Any] | None:
        if user_text is None and assistant_text is None:
            user_text = text or ""
            assistant_text = ""
        if not (user_text or "").strip():
            return None
        bounded_user = (user_text or "")[: settings.max_message_context_chars]
        bounded_assistant = (assistant_text or "")[: settings.max_agent_output_tokens * 6]
        payload = f"PESAN PENGGUNA:\n{bounded_user}\n\nJAWABAN AGENT:\n{bounded_assistant}"
        try:
            res = await openrouter_client.chat_completion(
                messages=[
                    {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                    {"role": "user", "content": payload},
                ],
                model=MODEL_CATALOG["mimo_v2_5"].model_id,
                temperature=0.0,
                response_format={"type": "json_object"},
                max_tokens=settings.max_memory_judge_output_tokens,
                usage_context={
                    "group_id": group_id,
                    "thread_id": thread_id,
                    "role_id": role_id.value if role_id else "memory_judge",
                },
            )
            data = json.loads(res.content)
            if not data.get("should_store"):
                return data
            items = data.get("items") or []
            # compatibility dengan shape lama
            if not items and data.get("key") and data.get("value"):
                items = [data]
            for item in items[:5]:
                if not item.get("key") or not item.get("value"):
                    continue
                scope = MemoryScope.SHARED if item.get("scope") == "shared" else MemoryScope.ROLE
                if scope == MemoryScope.ROLE and role_id is None:
                    continue
                try:
                    mem_type = MemoryType(item.get("memory_type", "fact"))
                except ValueError:
                    mem_type = MemoryType.FACT
                await memory_service.set_memory(
                    scope=scope,
                    key=str(item["key"])[:120],
                    value=str(item["value"])[:4000],
                    changed_by_actor=actor_id,
                    role_id=role_id if scope == MemoryScope.ROLE else None,
                    changed_by_role=role_id,
                    reason=item.get("reason", "Memory Judge"),
                    memory_type=mem_type,
                    group_id=group_id,
                )
            return data
        except (json.JSONDecodeError, ValueError, TypeError):
            return None
        except Exception:
            return None


memory_judge = MemoryJudge()
