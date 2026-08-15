"""Tool registry with progressive discovery metadata for Morrow."""

import re
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.core.types import RoleID


class ToolCapability(str, Enum):
    READ = "read"
    PREPARE = "prepare"
    COMMIT = "commit"


@dataclass
class RegisteredTool:
    name: str
    func: Callable[..., Coroutine[Any, Any, Any]]
    description: str
    parameters: dict[str, Any]
    eligible_roles: set[RoleID] | None = None
    domain: str = "utility"
    capability: ToolCapability = ToolCapability.READ
    risk: str = "low"
    side_effect: bool = False
    auth_required: bool = False
    output_trust: str = "trusted_internal"
    cost_class: str = "local"
    retry_safe: bool = True
    keywords: set[str] = field(default_factory=set)

    def descriptor(self) -> dict[str, Any]:
        """Return compact discovery metadata without loading the full JSON schema."""
        return {
            "name": self.name,
            "domain": self.domain,
            "description": self.description,
            "capability": self.capability.value,
            "risk": self.risk,
            "side_effect": self.side_effect,
            "auth_required": self.auth_required,
            "output_trust": self.output_trust,
            "cost_class": self.cost_class,
            "retry_safe": self.retry_safe,
        }


class ToolRegistry:
    """Registry for executable tools plus compact metadata used by discovery."""

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
        domain: str = "utility",
        capability: ToolCapability | str = ToolCapability.READ,
        risk: str = "low",
        side_effect: bool | None = None,
        auth_required: bool = False,
        output_trust: str = "trusted_internal",
        cost_class: str = "local",
        retry_safe: bool | None = None,
        keywords: set[str] | None = None,
    ) -> None:
        capability_value = (
            capability if isinstance(capability, ToolCapability) else ToolCapability(capability)
        )
        inferred_side_effect = capability_value == ToolCapability.COMMIT
        inferred_retry_safe = capability_value == ToolCapability.READ
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
            domain=domain,
            capability=capability_value,
            risk=risk,
            side_effect=inferred_side_effect if side_effect is None else side_effect,
            auth_required=auth_required,
            output_trust=output_trust,
            cost_class=cost_class,
            retry_safe=inferred_retry_safe if retry_safe is None else retry_safe,
            keywords={item.lower() for item in (keywords or set())},
        )

    def get_tool(self, name: str) -> Callable[..., Coroutine[Any, Any, Any]] | None:
        tool = self._tools.get(name)
        return tool.func if tool else None

    def get_registered_tool(self, name: str) -> RegisteredTool | None:
        return self._tools.get(name)

    @staticmethod
    def _eligible(tool: RegisteredTool, role: RoleID | None) -> bool:
        return not (role is not None and tool.eligible_roles and role not in tool.eligible_roles)

    def list_tools(self) -> dict[str, str]:
        return {name: tool.description for name, tool in self._tools.items()}

    def descriptors(
        self,
        role: RoleID | None = None,
        names: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for tool in self._tools.values():
            if not self._eligible(tool, role):
                continue
            if names is not None and tool.name not in names:
                continue
            result.append(tool.descriptor())
        return result

    @staticmethod
    def _tokens(value: str) -> set[str]:
        return {
            token
            for token in re.findall(r"[a-z0-9_]+", value.lower())
            if len(token) >= 2
        }

    def search_tools(
        self,
        query: str,
        role: RoleID | None = None,
        *,
        limit: int = 8,
    ) -> list[str]:
        """Return ranked tool names using deterministic lexical discovery."""
        query_tokens = self._tokens(query)
        if not query_tokens:
            return []

        ranked: list[tuple[int, str]] = []
        query_lower = query.lower()
        for tool in self._tools.values():
            if not self._eligible(tool, role):
                continue
            haystack = " ".join(
                [
                    tool.name,
                    tool.domain,
                    tool.description,
                    " ".join(sorted(tool.keywords)),
                ]
            ).lower()
            haystack_tokens = self._tokens(haystack)
            overlap = len(query_tokens & haystack_tokens)
            score = overlap * 4
            if tool.name.lower() in query_lower:
                score += 12
            if tool.domain.lower() in query_tokens:
                score += 3
            if any(keyword in query_tokens for keyword in tool.keywords):
                score += 3
            if score > 0:
                ranked.append((score, tool.name))

        ranked.sort(key=lambda item: (-item[0], item[1]))
        return [name for _, name in ranked[: max(1, limit)]]

    def openai_tool_schemas(
        self,
        role: RoleID | None = None,
        names: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        schemas: list[dict[str, Any]] = []
        for tool in self._tools.values():
            if not self._eligible(tool, role):
                continue
            if names is not None and tool.name not in names:
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
