"""Progressive local tool discovery exposed as a compact meta-tool."""

from typing import Any

from src.core.config import settings
from src.core.types import RoleID
from src.tools.registry import ToolCapability, tool_registry


async def morrow_tool_search(query: str, _role: str) -> dict[str, Any]:
    """Search registered local capabilities without exposing every JSON schema."""
    role = RoleID(_role)
    names = tool_registry.search_tools(
        query,
        role,
        limit=settings.max_discovered_tools_per_query,
    )
    names = [name for name in names if name != "morrow_tool_search"]
    return {
        "query": query,
        "names": names,
        "tools": tool_registry.descriptors(role, set(names)),
    }


def ensure_discovery_tool_registered() -> None:
    if tool_registry.get_tool("morrow_tool_search") is not None:
        return
    tool_registry.register_tool(
        "morrow_tool_search",
        morrow_tool_search,
        description=(
            "Cari capability/tool lokal Morrow yang relevan. Hasil hanya metadata ringkas; "
            "schema lengkap tool terpilih akan tersedia pada ronde berikutnya."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Capability yang dibutuhkan, contoh: browser form, calculator, email read."
                    ),
                }
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        domain="meta",
        capability=ToolCapability.READ,
        risk="low",
        side_effect=False,
        output_trust="trusted_internal",
        cost_class="local",
        retry_safe=True,
        keywords={"tool", "capability", "discovery", "find", "cari"},
    )
