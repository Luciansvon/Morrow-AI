"""Daftar alat, metadata schema, dan registri eksekutor fungsi di Morrow."""

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from src.core.types import RoleID


@dataclass
class RegisteredTool:
    name: str
    func: Callable[..., Coroutine[Any, Any, Any]]
    description: str
    parameters: dict[str, Any]
    eligible_roles: set[RoleID] | None = None


class ToolRegistry:
    """Registri fungsi alat yang dapat dipanggil oleh agen."""

    def __init__(self):
        self._tools: dict[str, RegisteredTool] = {}

    def register_tool(
        self,
        name: str,
        func: Callable[..., Coroutine[Any, Any, Any]],
        *,
        description: str | None = None,
        parameters: dict[str, Any] | None = None,
        eligible_roles: set[RoleID] | None = None,
    ) -> None:
        self._tools[name] = RegisteredTool(
            name=name,
            func=func,
            description=description or getattr(func, "__doc__", "") or "",
            parameters=parameters
            or {
                "type": "object",
                "properties": {},
                "additionalProperties": True,
            },
            eligible_roles=eligible_roles,
        )

    def get_tool(self, name: str) -> Callable[..., Coroutine[Any, Any, Any]] | None:
        tool = self._tools.get(name)
        return tool.func if tool else None

    def list_tools(self) -> dict[str, str]:
        return {name: tool.description for name, tool in self._tools.items()}

    def openai_tool_schemas(self, role: RoleID | None = None) -> list[dict[str, Any]]:
        schemas: list[dict[str, Any]] = []
        for tool in self._tools.values():
            if role is not None and tool.eligible_roles and role not in tool.eligible_roles:
                continue
            schemas.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    },
                }
            )
        return schemas


tool_registry = ToolRegistry()
