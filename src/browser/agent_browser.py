"""Concrete agent-browser CLI backend with isolated per-task sessions."""

import asyncio
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, ClassVar

from src.browser.base import BrowserActionClass, BrowserBackend, BrowserBackendUnavailableError
from src.core.config import settings


class AgentBrowserBackend(BrowserBackend):
    """Production local-browser backend backed by the vercel-labs agent-browser CLI."""

    _ACTION_CLASS_ORDER: ClassVar[dict[BrowserActionClass, int]] = {
        BrowserActionClass.READ: 0,
        BrowserActionClass.PREPARE: 1,
        BrowserActionClass.COMMIT: 2,
    }
    _MIN_ACTION_CLASS: ClassVar[dict[str, BrowserActionClass]] = {
        "fill": BrowserActionClass.PREPARE,
        "type": BrowserActionClass.PREPARE,
        "select": BrowserActionClass.PREPARE,
        "check": BrowserActionClass.PREPARE,
        "uncheck": BrowserActionClass.PREPARE,
        "scroll": BrowserActionClass.PREPARE,
        "click": BrowserActionClass.COMMIT,
        "press": BrowserActionClass.COMMIT,
    }

    def __init__(
        self,
        executable: str | None = None,
        *,
        timeout_seconds: float | None = None,
        headed: bool | None = None,
    ):
        self.executable = executable or settings.browser_agent_executable
        self.timeout_seconds = timeout_seconds or settings.browser_timeout_seconds
        self.headed = settings.browser_headed if headed is None else headed

    @staticmethod
    def _session_name(task_space: str) -> str:
        raw = task_space.strip() or "morrow"
        sanitized = re.sub(r"[^A-Za-z0-9_.-]+", "-", raw).strip("-")
        if sanitized and len(sanitized) <= 64:
            return sanitized
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
        prefix = sanitized[:40].strip("-") or "morrow"
        return f"{prefix}-{digest}"

    def _resolved_executable(self) -> str:
        configured = self.executable.strip()
        explicit = Path(configured).expanduser()
        if explicit.parent != Path(".") and explicit.exists() and explicit.is_file():
            return str(explicit)
        return shutil.which(configured) or configured

    def _command_argv(self, task_space: str, *command: str) -> list[str]:
        session = self._session_name(task_space)
        executable = self._resolved_executable()
        base = [executable, "--session", session, "--json"]
        if self.headed:
            base.append("--headed")
        base.extend(command)

        # npm global binaries on Windows are commonly .cmd/.bat shims. Resolve and
        # invoke them explicitly through COMSPEC so CreateProcess behavior is stable.
        if os.name == "nt" and Path(executable).suffix.lower() in {".cmd", ".bat"}:
            comspec = os.environ.get("COMSPEC") or "cmd.exe"
            return [comspec, "/d", "/s", "/c", subprocess.list2cmdline(base)]
        return base

    async def _run(self, task_space: str, *command: str) -> dict[str, Any]:
        argv = self._command_argv(task_space, *command)
        try:
            process = await asyncio.create_subprocess_exec(
                *argv,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            raise BrowserBackendUnavailableError(
                f"Browser backend '{self.executable}' tidak ditemukan. "
                "Install agent-browser lalu aktifkan BROWSER_ENABLED."
            ) from exc

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout_seconds,
            )
        except TimeoutError:
            process.kill()
            await process.communicate()
            raise TimeoutError("Browser action melewati batas waktu.") from None

        out = stdout.decode("utf-8", errors="replace").strip()
        err = stderr.decode("utf-8", errors="replace").strip()
        if process.returncode != 0:
            raise RuntimeError(err or out or f"agent-browser keluar dengan kode {process.returncode}")

        if not out:
            return {"success": True}
        try:
            parsed = json.loads(out)
        except json.JSONDecodeError:
            return {"success": True, "output": out}
        return parsed if isinstance(parsed, dict) else {"success": True, "result": parsed}

    async def open(self, url: str, *, task_space: str) -> dict[str, Any]:
        return await self._run(task_space, "open", url)

    async def snapshot(self, *, task_space: str) -> dict[str, Any]:
        # Interactive + compact keeps the model context small while retaining actionable refs.
        return await self._run(task_space, "snapshot", "-i", "-c")

    async def screenshot(self, *, task_space: str) -> dict[str, Any]:
        return await self._run(task_space, "screenshot")

    @classmethod
    def _validate_action_class(
        cls,
        action: str,
        requested: BrowserActionClass,
    ) -> None:
        minimum = cls._MIN_ACTION_CLASS.get(action)
        if minimum is None:
            raise ValueError(f"Browser action tidak didukung: {action}")
        if cls._ACTION_CLASS_ORDER[requested] < cls._ACTION_CLASS_ORDER[minimum]:
            raise ValueError(
                f"Browser action '{action}' minimal diklasifikasikan sebagai {minimum.value}."
            )

    async def interact(
        self,
        action: str,
        parameters: dict[str, Any],
        *,
        task_space: str,
        action_class: BrowserActionClass,
    ) -> dict[str, Any]:
        self._validate_action_class(action, action_class)
        target = str(parameters.get("target") or "").strip()

        if action in {"fill", "type", "select"}:
            value = str(parameters.get("value") or "")
            if not target:
                raise ValueError("Browser target wajib diisi.")
            return await self._run(task_space, action, target, value)
        if action in {"check", "uncheck", "click"}:
            if not target:
                raise ValueError("Browser target wajib diisi.")
            return await self._run(task_space, action, target)
        if action == "press":
            key = str(parameters.get("key") or "").strip()
            if not key:
                raise ValueError("Browser key wajib diisi.")
            return await self._run(task_space, "press", key)
        if action == "scroll":
            direction = str(parameters.get("direction") or "down").lower()
            if direction not in {"up", "down", "left", "right"}:
                raise ValueError("Arah scroll tidak valid.")
            amount = str(parameters.get("amount") or "500")
            return await self._run(task_space, "scroll", direction, amount)
        raise ValueError(f"Browser action tidak didukung: {action}")

    async def handoff_to_user(self, *, task_space: str, reason: str) -> dict[str, Any]:
        return {
            "success": True,
            "status": "waiting_user",
            "task_space": self._session_name(task_space),
            "reason": reason,
        }

    async def take_back_control(self, *, task_space: str) -> dict[str, Any]:
        snapshot = await self.snapshot(task_space=task_space)
        return {
            "success": True,
            "status": "resumed",
            "task_space": self._session_name(task_space),
            "snapshot": snapshot,
        }


agent_browser_backend = AgentBrowserBackend()
