"""Daftar alat dan registri eksekutor fungsi di Morrow v0.2."""

from collections.abc import Callable, Coroutine
from typing import Any


class ToolRegistry:
    """Registri fungsi alat yang dapat dipanggil oleh agen."""

    def __init__(self):
        self._tools: dict[str, Callable[..., Coroutine[Any, Any, Any]]] = {}

    def register_tool(self, name: str, func: Callable[..., Coroutine[Any, Any, Any]]) -> None:
        self._tools[name] = func

    def get_tool(self, name: str) -> Callable[..., Coroutine[Any, Any, Any]] | None:
        return self._tools.get(name)

    def list_tools(self) -> dict[str, str]:
        return {name: getattr(func, "__doc__", "") or "" for name, func in self._tools.items()}


tool_registry = ToolRegistry()
