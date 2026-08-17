"""LLM-facing browser tools backed by the configured BrowserBackend."""

import hashlib
import json
from typing import Any

from src.browser.agent_browser import agent_browser_backend  # compatibility test hook
from src.browser.base import BrowserActionClass
from src.browser.provider import get_browser_backend
from src.core.config import settings
from src.tools.registry import ToolCapability, tool_registry

__all__ = ["agent_browser_backend", "browser_state_fingerprint"]


def _fingerprint_snapshot(snapshot: dict[str, Any]) -> str:
    canonical = json.dumps(snapshot, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def browser_state_fingerprint(task_space: str) -> str:
    """Fingerprint the current semantic browser state for approval binding."""
    snapshot = await get_browser_backend().snapshot(task_space=task_space)
    return _fingerprint_snapshot(snapshot)


async def _verify_expected_state(task_space: str, expected_state_hash: str | None) -> None:
    if not expected_state_hash:
        return
    current = await browser_state_fingerprint(task_space)
    if current != expected_state_hash:
        raise ValueError(
            "BROWSER_STATE_CHANGED: halaman/form berubah setelah approval dibuat; approval lama tidak boleh dieksekusi."
        )


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


async def browser_select(target: str, value: str, _task_space: str) -> dict[str, Any]:
    return await get_browser_backend().interact(
        "select",
        {"target": target, "value": value},
        task_space=_task_space,
        action_class=BrowserActionClass.PREPARE,
    )


async def browser_check(target: str, _task_space: str) -> dict[str, Any]:
    return await get_browser_backend().interact(
        "check",
        {"target": target},
        task_space=_task_space,
        action_class=BrowserActionClass.PREPARE,
    )


async def browser_uncheck(target: str, _task_space: str) -> dict[str, Any]:
    return await get_browser_backend().interact(
        "uncheck",
        {"target": target},
        task_space=_task_space,
        action_class=BrowserActionClass.PREPARE,
    )


async def browser_scroll(
    _task_space: str,
    direction: str = "down",
    amount: int = 500,
) -> dict[str, Any]:
    return await get_browser_backend().interact(
        "scroll",
        {"direction": direction, "amount": amount},
        task_space=_task_space,
        action_class=BrowserActionClass.PREPARE,
    )


async def browser_click(
    target: str,
    _task_space: str,
    _state_hash: str | None = None,
    _approved: bool = False,
) -> dict[str, Any]:
    if not _approved:
        raise PermissionError("BROWSER_COMMIT_APPROVAL_REQUIRED")
    await _verify_expected_state(_task_space, _state_hash)
    return await get_browser_backend().interact(
        "click",
        {"target": target},
        task_space=_task_space,
        action_class=BrowserActionClass.COMMIT,
        approved=True,
    )


async def browser_press(
    key: str,
    _task_space: str,
    _state_hash: str | None = None,
    _approved: bool = False,
) -> dict[str, Any]:
    if not _approved:
        raise PermissionError("BROWSER_COMMIT_APPROVAL_REQUIRED")
    await _verify_expected_state(_task_space, _state_hash)
    return await get_browser_backend().interact(
        "press",
        {"key": key},
        task_space=_task_space,
        action_class=BrowserActionClass.COMMIT,
        approved=True,
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
        "Ambil snapshot compact elemen interaktif halaman browser aktif untuk reasoning.",
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
        ("browser_select", browser_select, "Pilih opsi"),
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
            keywords={"browser", "form", name.removeprefix("browser_"), "isi", "pilih", "prepare"},
        )
    for name, func, verb in (
        ("browser_check", browser_check, "Centang"),
        ("browser_uncheck", browser_uncheck, "Hilangkan centang"),
    ):
        _register(
            name,
            func,
            f"{verb} checkbox/radio secara lokal tanpa submit.",
            {
                "type": "object",
                "properties": {"target": {"type": "string"}},
                "required": ["target"],
                "additionalProperties": False,
            },
            capability=ToolCapability.PREPARE,
            risk="medium",
            side_effect=False,
            retry_safe=False,
            keywords={"browser", "form", "checkbox", "check", "centang", "prepare"},
        )
    _register(
        "browser_scroll",
        browser_scroll,
        "Scroll halaman tanpa melakukan side effect eksternal.",
        {
            "type": "object",
            "properties": {
                "direction": {
                    "type": "string",
                    "enum": ["up", "down", "left", "right"],
                    "default": "down",
                },
                "amount": {"type": "integer", "minimum": 1, "maximum": 10000, "default": 500},
            },
            "additionalProperties": False,
        },
        capability=ToolCapability.PREPARE,
        risk="low",
        side_effect=False,
        retry_safe=True,
        keywords={"browser", "scroll", "gulir", "atas", "bawah", "page"},
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
    _register(
        "browser_press",
        browser_press,
        "Tekan tombol keyboard pada browser. Diposisikan sebagai COMMIT karena Enter/shortcut dapat mengirim form atau memicu side effect.",
        {
            "type": "object",
            "properties": {"key": {"type": "string"}},
            "required": ["key"],
            "additionalProperties": False,
        },
        capability=ToolCapability.COMMIT,
        risk="high",
        side_effect=True,
        retry_safe=False,
        keywords={"browser", "press", "keyboard", "enter", "submit", "tekan"},
    )
