"""Ego Lite browser backend using the official ego-browser Node.js bridge."""

import asyncio
import hashlib
import json
import platform
import re
import shutil
from pathlib import Path
from typing import Any, ClassVar

from src.browser.base import BrowserActionClass, BrowserBackend, BrowserBackendUnavailableError
from src.core.config import settings


class EgoLiteBackend(BrowserBackend):
    """Provider adapter for citrolabs/ego-lite via the official `ego-browser nodejs` runtime."""

    _ACTION_CLASS_ORDER: ClassVar[dict[BrowserActionClass, int]] = {
        BrowserActionClass.READ: 0,
        BrowserActionClass.PREPARE: 1,
        BrowserActionClass.COMMIT: 2,
    }
    _MIN_ACTION_CLASS: ClassVar[dict[str, BrowserActionClass]] = {
        "fill": BrowserActionClass.PREPARE,
        "type": BrowserActionClass.PREPARE,
        "scroll": BrowserActionClass.PREPARE,
        "wait": BrowserActionClass.PREPARE,
        "click": BrowserActionClass.COMMIT,
        "press": BrowserActionClass.COMMIT,
    }

    def __init__(
        self,
        executable: str | None = None,
        *,
        timeout_seconds: float | None = None,
    ):
        self.executable = executable or settings.browser_ego_executable
        self.timeout_seconds = timeout_seconds or settings.browser_timeout_seconds

    @staticmethod
    def _space_name(task_space: str) -> str:
        raw = task_space.strip() or "morrow"
        sanitized = re.sub(r"[^A-Za-z0-9_.-]+", "-", raw).strip("-")
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:10]
        prefix = sanitized[:48].strip("-") or "morrow"
        return f"morrow-{prefix}-{digest}"[:72]

    def _command_available(self) -> bool:
        return bool(shutil.which(self.executable) or Path(self.executable).exists())

    def _check_platform_availability(self) -> None:
        # Ego Lite documents macOS as the supported platform today. Do not hard-block
        # future Windows/Linux builds if a real ego-browser executable is present.
        current = platform.system()
        if current != "Darwin" and not self._command_available():
            raise BrowserBackendUnavailableError(
                "Ego Lite saat ini resmi tersedia di macOS dan executable 'ego-browser' "
                f"tidak terdeteksi di {current}. Browser Morrow tetap fail-closed."
            )

    @staticmethod
    def _json_literal(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False)

    @staticmethod
    def _parse_output(stdout: str) -> dict[str, Any]:
        for raw_line in reversed(stdout.splitlines()):
            line = raw_line.strip()
            if not line:
                continue
            candidates = [line]
            brace = line.find("{")
            if brace > 0:
                candidates.append(line[brace:])
            for candidate in candidates:
                try:
                    parsed = json.loads(candidate)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict):
                    return parsed
                return {"success": True, "result": parsed}
        return {"success": True, "output": stdout.strip()} if stdout.strip() else {"success": True}

    async def _run_script(self, script: str) -> dict[str, Any]:
        self._check_platform_availability()
        try:
            process = await asyncio.create_subprocess_exec(
                self.executable,
                "nodejs",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            raise BrowserBackendUnavailableError(
                "Browser backend Ego Lite tidak tersedia: command 'ego-browser' tidak ditemukan. "
                "Install dan selesaikan onboarding Ego Lite terlebih dahulu."
            ) from exc

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(script.encode("utf-8")),
                timeout=self.timeout_seconds,
            )
        except TimeoutError:
            process.kill()
            await process.communicate()
            raise TimeoutError("Ego Lite browser action melewati batas waktu.") from None

        out = stdout.decode("utf-8", errors="replace")
        err = stderr.decode("utf-8", errors="replace").strip()
        if process.returncode != 0:
            lower = err.lower()
            if "not found" in lower or ("command" in lower and "ego-browser" in lower):
                raise BrowserBackendUnavailableError(err or "ego-browser tidak tersedia")
            raise RuntimeError(err or out.strip() or f"ego-browser keluar dengan kode {process.returncode}")
        return self._parse_output(out)

    def _space_prelude(self, task_space: str) -> str:
        name = self._space_name(task_space)
        return f"const task = await useOrCreateTaskSpace({self._json_literal(name)});\n"

    async def open(self, url: str, *, task_space: str) -> dict[str, Any]:
        script = self._space_prelude(task_space) + (
            f"await openOrReuseTab({self._json_literal(url)}, {{ wait: true, timeout: 20 }});\n"
            "const page = await pageInfo();\n"
            "cliLog(JSON.stringify({success:true, provider:'ego-lite', taskSpaceId:task.id, page}));\n"
        )
        return await self._run_script(script)

    async def snapshot(self, *, task_space: str) -> dict[str, Any]:
        script = self._space_prelude(task_space) + (
            "const snapshot = await snapshotText();\n"
            "cliLog(JSON.stringify({success:true, provider:'ego-lite', taskSpaceId:task.id, snapshot}));\n"
        )
        return await self._run_script(script)

    async def screenshot(self, *, task_space: str) -> dict[str, Any]:
        script = self._space_prelude(task_space) + (
            "const capture = await captureScreenshot();\n"
            "cliLog(JSON.stringify({success:true, provider:'ego-lite', taskSpaceId:task.id, capture}));\n"
        )
        return await self._run_script(script)

    @classmethod
    def _validate_action_class(cls, action: str, requested: BrowserActionClass) -> None:
        minimum = cls._MIN_ACTION_CLASS.get(action)
        if minimum is None:
            raise ValueError(f"Browser action Ego Lite tidak didukung: {action}")
        if cls._ACTION_CLASS_ORDER[requested] < cls._ACTION_CLASS_ORDER[minimum]:
            raise ValueError(f"Browser action '{action}' minimal diklasifikasikan sebagai {minimum.value}.")

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
        prelude = self._space_prelude(task_space)

        if action == "fill":
            value = str(parameters.get("value") or "")
            if not target:
                raise ValueError("Browser target wajib diisi.")
            body = f"await fillInput({self._json_literal(target)}, {self._json_literal(value)});\n"
        elif action == "type":
            value = str(parameters.get("value") or "")
            if not target:
                raise ValueError("Browser target wajib diisi.")
            # Keep PREPARE semantics: target-focused generic click is classified COMMIT
            # by Morrow, so text entry uses Ego Lite's input helper directly.
            body = f"await fillInput({self._json_literal(target)}, {self._json_literal(value)});\n"
        elif action == "click":
            if not target:
                raise ValueError("Browser target wajib diisi.")
            body = f"await click({self._json_literal(target)});\n"
        elif action == "press":
            key = str(parameters.get("key") or "").strip()
            if not key:
                raise ValueError("Browser key wajib diisi.")
            body = f"await pressKey({self._json_literal(key)});\n"
        elif action == "scroll":
            direction = str(parameters.get("direction") or "down").lower()
            if direction not in {"up", "down", "left", "right"}:
                raise ValueError("Arah scroll tidak valid.")
            amount = int(parameters.get("amount") or 500)
            dx = -amount if direction == "left" else amount if direction == "right" else 0
            dy = -amount if direction == "up" else amount if direction == "down" else 0
            body = f"await scroll({{ dx: {dx}, dy: {dy} }});\n"
        elif action == "wait":
            seconds = float(parameters.get("seconds") or 1)
            body = f"await wait({seconds});\n"
        else:
            raise ValueError(f"Browser action Ego Lite tidak didukung: {action}")

        script = prelude + body + (
            "const page = await pageInfo();\n"
            f"cliLog(JSON.stringify({{success:true, provider:'ego-lite', action:{self._json_literal(action)}, taskSpaceId:task.id, page}}));\n"
        )
        return await self._run_script(script)

    async def handoff_to_user(self, *, task_space: str, reason: str) -> dict[str, Any]:
        script = self._space_prelude(task_space) + (
            "const handoff = await handOffTaskSpace(task.id);\n"
            f"cliLog(JSON.stringify({{success:Boolean(handoff && handoff.done), provider:'ego-lite', status:handoff && handoff.done ? 'waiting_user' : 'handoff_skipped', reason:{self._json_literal(reason)}, handoff}}));\n"
        )
        return await self._run_script(script)

    async def take_back_control(self, *, task_space: str) -> dict[str, Any]:
        name = self._space_name(task_space)
        script = (
            f"const task = await takeOverTaskSpace({self._json_literal(name)});\n"
            "const snapshot = await snapshotText();\n"
            "cliLog(JSON.stringify({success:true, provider:'ego-lite', status:'resumed', taskSpaceId:task.id, snapshot}));\n"
        )
        return await self._run_script(script)


ego_lite_backend = EgoLiteBackend()
