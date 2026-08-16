"""LLM-facing browser tools backed by the configured BrowserBackend."""

from typing import Any

from src.browser.agent_browser import agent_browser_backend  # compatibility test/legacy hook
from src.browser.base import BrowserActionClass
from src.browser.provider import get_browser_backend
from src.core.config import settings
from src.tools.registry import ToolCapability, tool_registry


async def browser_open(url: str, _task_space: str) -> dict[str, Any]:
    return await get_browser_backend().open(url, task_space=_task_space)


async def browser_snapshot(_task_space: str) -> dict[str, Any]:
    return await get_browser_backend().snapshot(task_space=_task_space)


async def browser_screenshot(_task_space: str) -> dict[str, Any]:
    return await get_browser_backend().screenshot(task_space=_task_space)


async def browser_fill(target: str, value: str, _task_space: str) -> dict[str, Any]:
    return await get_browser_backend().interact(
        "fill",
        {"target": target, "value": value},
        task_space=_task_space,
        action_class=BrowserActionClass.PREPARE,
    )


async def browser_type(target: str, value: str, _task_space: str) -> dict[str, Any]:
    return await get_browser_backend().interact(
        "type",
        {"target": target, "value": value},
        task_space=_task_space,
        action_class=BrowserActionClass.PREPARE,
    )


async def browser_click(target: str, _task_space: str) -> dict[str, Any]:
    return await get_browser_backend().interact(
        "click",
        {"target": target},
        task_space=_task_space,
        action_class=BrowserActionClass.COMMIT,
    )


def _register(
    name: str,
    func,
    description: str,
    parameters: dict[str, Any],
    *,
    capability: ToolCapability,
    risk: str,
    side_effect: bool,
    retry_safe: bool,
    keywords: set[str],
) -> None:
    if tool_registry.get_tool(name) is not None:
        return
    tool_registry.register_tool(
        name,
        func,
        description=description,
        parameters=parameters,
        domain="browser",
        capability=capability,
        risk=risk,
        side_effect=side_effect,
        auth_required=False,
        output_trust="external",
        cost_class="local_browser",
        retry_safe=retry_safe,
        keywords=keywords,
    )


def ensure_browser_tools_registered() -> None:
    if not settings.browser_enabled:
        return

    _register(
        "browser_open",
        browser_open,
        "Buka URL di browser task-space terisolasi tanpa melakukan submit atau mutasi eksternal.",
        {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
            "additionalProperties": False,
        },
        capability=ToolCapability.READ,
        risk="low",
        side_effect=False,
        retry_safe=True,
        keywords={"browser", "open", "url", "website", "web", "buka", "halaman"},
    )
    _register(
        "browser_snapshot",
        browser_snapshot,
        "Ambil snapshot elemen interaktif halaman browser aktif untuk reasoning.",
        {"type": "object", "properties": {}, "additionalProperties": False},
        capability=ToolCapability.READ,
        risk="low",
        side_effect=False,
        retry_safe=True,
        keywords={"browser", "snapshot", "inspect", "page", "halaman", "lihat"},
    )
    _register(
        "browser_screenshot",
        browser_screenshot,
        "Ambil screenshot halaman browser aktif.",
        {"type": "object", "properties": {}, "additionalProperties": False},
        capability=ToolCapability.READ,
        risk="low",
        side_effect=False,
        retry_safe=True,
        keywords={"browser", "screenshot", "visual", "page", "halaman"},
    )
    for name, func, verb in (
        ("browser_fill", browser_fill, "Isi field"),
        ("browser_type", browser_type, "Ketik ke field"),
    ):
        _register(
            name,
            func,
            f"{verb} pada halaman tanpa melakukan submit. Gunakan snapshot ref seperti @e1.",
            {
                "type": "object",
                "properties": {
                    "target": {"type": "string"},
                    "value": {"type": "string"},
                },
                "required": ["target", "value"],
                "additionalProperties": False,
            },
            capability=ToolCapability.PREPARE,
            risk="medium",
            side_effect=False,
            retry_safe=False,
            keywords={"browser", "form", "fill", "type", "isi", "ketik", "prepare"},
        )
    _register(
        "browser_click",
        browser_click,
        "Klik elemen yang dapat menimbulkan side effect. Selalu diperlakukan sebagai COMMIT dan wajib approval.",
        {
            "type": "object",
            "properties": {"target": {"type": "string"}},
            "required": ["target"],
            "additionalProperties": False,
        },
        capability=ToolCapability.COMMIT,
        risk="high",
        side_effect=True,
        retry_safe=False,
        keywords={"browser", "click", "submit", "send", "purchase", "delete", "klik"},
    )
