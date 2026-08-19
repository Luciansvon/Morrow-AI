"""Plain-Markdown mirror of durable memory. Obsidian can open it, Morrow does not depend on it."""

import asyncio
import hashlib
import re
from pathlib import Path

from src.core.config import settings
from src.core.types import MemoryScope, RoleID
from src.storage.sqlite import db

_SAFE_COMPONENT_RE = re.compile(r"[^A-Za-z0-9._-]+")


class MarkdownMemoryVault:
    @staticmethod
    def _safe_component(value: str) -> str:
        raw = value.strip()
        cleaned = _SAFE_COMPONENT_RE.sub("_", raw).strip("._")[:80]
        # Preserve existing paths for already-safe, short identifiers. If sanitization or
        # truncation changed the identifier, append a stable digest so `team/a` cannot collide
        # with the genuinely distinct safe ID `team_a`.
        if cleaned and cleaned == raw and len(raw) <= 80:
            return cleaned
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
        if cleaned:
            return f"{cleaned[:64]}--{digest}"
        return "group_" + digest

    @classmethod
    def _target_path(
        cls,
        group_id: str,
        scope: MemoryScope,
        role_id: RoleID | None,
    ) -> Path:
        group_dir = Path(settings.memory_vault_dir) / cls._safe_component(group_id)
        if scope == MemoryScope.SHARED:
            return group_dir / "shared.md"
        assert role_id is not None
        return group_dir / "roles" / f"{role_id.value}.md"

    @staticmethod
    def _render(
        group_id: str,
        scope: MemoryScope,
        role_id: RoleID | None,
        rows: list[dict[str, str]],
    ) -> str:
        title = "Shared Memory" if scope == MemoryScope.SHARED else f"{role_id.value.title()} Memory"
        lines = [
            f"# Morrow {title}",
            "",
            "<!-- MORROW-MANAGED MIRROR: SQLite remains the source of truth. -->",
            f"- group: `{group_id}`",
            f"- scope: `{scope.value}`",
        ]
        if role_id:
            lines.append(f"- role: `{role_id.value}`")
        lines.append("")
        for row in rows:
            lines.extend(
                [
                    f"## {row['key']}",
                    "",
                    f"- type: `{row['memory_type']}`",
                    f"- updated: `{row['updated_at']}`",
                    "",
                    str(row["value"]),
                    "",
                ]
            )
        if not rows:
            lines.extend(["_Belum ada memori._", ""])
        return "\n".join(lines)

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(path)

    async def sync_scope(
        self,
        group_id: str,
        scope: MemoryScope,
        role_id: RoleID | None = None,
    ) -> Path:
        if scope == MemoryScope.ROLE and role_id is None:
            raise ValueError("role_id wajib untuk role memory vault")
        if scope == MemoryScope.SHARED and role_id is not None:
            raise ValueError("shared memory vault tidak menerima role_id")
        if scope == MemoryScope.SHARED:
            rows = await db.fetch_all(
                """SELECT key, value, memory_type, updated_at FROM memories
                   WHERE group_id=? AND scope='shared' ORDER BY key""",
                (group_id,),
            )
        else:
            rows = await db.fetch_all(
                """SELECT key, value, memory_type, updated_at FROM memories
                   WHERE group_id=? AND scope='role' AND role_id=? ORDER BY key""",
                (group_id, role_id.value),
            )
        path = self._target_path(group_id, scope, role_id)
        content = self._render(group_id, scope, role_id, rows)
        await asyncio.to_thread(self._atomic_write, path, content)
        return path

    async def sync_all(self) -> int:
        rows = await db.fetch_all(
            "SELECT DISTINCT group_id, scope, role_id FROM memories ORDER BY group_id, scope, role_id"
        )
        count = 0
        for row in rows:
            scope = MemoryScope(row["scope"])
            role = RoleID(row["role_id"]) if row["role_id"] else None
            await self.sync_scope(row["group_id"], scope, role)
            count += 1
        return count


memory_vault = MarkdownMemoryVault()
