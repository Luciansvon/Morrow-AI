"""Memory Judge menyimpan fakta/keputusan eksplisit dari exchange, bukan spekulasi agent."""

import hashlib
import json
import re
from typing import Any, ClassVar

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
    """Judge for implicit memory plus deterministic handling for explicit save commands."""

    _PREFIX_RE: ClassVar[re.Pattern[str]] = re.compile(
        r"^(?:(?:halo|hai|pagi|siang|sore|malam)\b[\s,:-]*)?"
        r"(?:(?:manager|marketing|advisor|tim|team|bot|morrow)\b[\s,:-]*)?"
        r"(?:(?:tolong|mohon|bantu|coba)\b[\s,:-]*)?",
        re.IGNORECASE,
    )
    _TYPE_MAP: ClassVar[dict[str, MemoryType]] = {
        "keputusan": MemoryType.DECISION,
        "decision": MemoryType.DECISION,
        "constraint": MemoryType.CONSTRAINT,
        "batasan": MemoryType.CONSTRAINT,
        "status": MemoryType.STATUS,
        "fakta": MemoryType.FACT,
        "fact": MemoryType.FACT,
    }
    _EXPLICIT_COMMANDS: ClassVar[list[tuple[re.Pattern[str], MemoryType | None]]] = [
        (
            re.compile(
                r"^(?:catat(?:kan)?|catet|ingat(?:kan)?|inget|simpan(?:kan)?)"
                r"(?:\s+ini)?\s+sebagai\s+"
                r"(keputusan|decision|constraint|batasan|status|fakta|fact)"
                r"(?:\s*:\s*|\s+bahwa\s+|\s+)(.+)$",
                re.IGNORECASE | re.DOTALL,
            ),
            None,
        ),
        (
            re.compile(
                r"^(?:catat(?:kan)?|catet|ingat(?:kan)?|inget|simpan(?:kan)?)\s+"
                r"(keputusan|decision|constraint|batasan|status|fakta|fact)\s*:\s*(.+)$",
                re.IGNORECASE | re.DOTALL,
            ),
            None,
        ),
        (
            re.compile(
                r"^(?:catat(?:kan)?|catet|ingat(?:kan)?|inget|simpan(?:kan)?)\s+bahwa\s+(.+)$",
                re.IGNORECASE | re.DOTALL,
            ),
            MemoryType.FACT,
        ),
        (
            re.compile(
                r"^(?:catat(?:kan)?|catet|ingat(?:kan)?|inget|simpan(?:kan)?)(?:\s+ini)?\s*:\s*(.+)$",
                re.IGNORECASE | re.DOTALL,
            ),
            MemoryType.FACT,
        ),
    ]

    @classmethod
    def parse_explicit_directive(cls, text: str) -> dict[str, Any] | None:
        """Parse explicit user memory command anchored near the message beginning."""
        stripped = text.strip()
        if not stripped:
            return None
        core = cls._PREFIX_RE.sub("", stripped).strip()
        if not core:
            return None

        for pattern, fixed_type in cls._EXPLICIT_COMMANDS:
            match = pattern.match(core)
            if not match:
                continue
            if fixed_type is not None:
                raw_type = "fakta"
                raw_value = match.group(1).strip()
                memory_type = fixed_type
            else:
                raw_type = match.group(1).strip()
                raw_value = match.group(2).strip()
                memory_type = cls._TYPE_MAP.get(raw_type.lower(), MemoryType.FACT)

            if not raw_value:
                return None
            tokens = re.findall(r"[a-z0-9]+", raw_value.lower())[:8]
            slug = "_".join(tokens)[:70] or memory_type.value
            digest = hashlib.sha256(raw_value.encode("utf-8")).hexdigest()[:10]
            key = f"explicit_{memory_type.value}_{slug}_{digest}"[:120]
            return {"key": key, "value": raw_value, "memory_type": memory_type}
        return None

    @classmethod
    async def commit_explicit_directive(
        cls,
        text: str,
        *,
        actor_id: str,
        role_id: RoleID | None,
        group_id: str,
    ) -> dict[str, Any] | None:
        """Persist an explicit user memory command and return only after durable write succeeds."""
        parsed = cls.parse_explicit_directive(text)
        if not parsed:
            return None
        item = await memory_service.set_memory(
            scope=MemoryScope.SHARED,
            key=parsed["key"],
            value=parsed["value"],
            changed_by_actor=actor_id,
            changed_by_role=role_id,
            reason="Explicit user memory command",
            memory_type=parsed["memory_type"],
            group_id=group_id,
        )
        return {
            "verified": True,
            "id": item.id,
            "key": item.key,
            "value": item.value,
            "memory_type": item.memory_type.value,
            "scope": item.scope.value,
        }

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
                data["stored_count"] = 0
                data["stored_items"] = []
                return data
            items = data.get("items") or []
            # compatibility dengan shape lama
            if not items and data.get("key") and data.get("value"):
                items = [data]
            stored_items: list[dict[str, Any]] = []
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
                stored = await memory_service.set_memory(
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
                stored_items.append(
                    {
                        "id": stored.id,
                        "key": stored.key,
                        "value": stored.value,
                        "scope": stored.scope.value,
                        "memory_type": stored.memory_type.value,
                    }
                )
            data["stored_count"] = len(stored_items)
            data["stored_items"] = stored_items
            return data
        except (json.JSONDecodeError, ValueError, TypeError):
            return None
        except Exception:
            return None


memory_judge = MemoryJudge()
