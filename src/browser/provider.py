"""Browser provider selection behind Morrow's provider-neutral contract."""

from __future__ import annotations

import shutil
from pathlib import Path

from src.browser.agent_browser import agent_browser_backend
from src.browser.base import BrowserBackend, BrowserBackendUnavailableError
from src.browser.ego_lite import ego_lite_backend
from src.core.config import settings


def _normalized_backend_name() -> str:
    return settings.browser_backend.strip().lower().replace("_", "-")


def configured_browser_executable() -> str:
    name = _normalized_backend_name()
    if name in {"ego", "ego-lite", "egolite"}:
        return settings.browser_ego_executable
    if name in {"agent-browser", "agentbrowser"}:
        return settings.browser_agent_executable
    raise BrowserBackendUnavailableError(
        f"Browser backend '{settings.browser_backend}' tidak dikenal. Gunakan 'agent-browser' atau 'ego-lite'."
    )


def browser_backend_availability() -> tuple[bool, str]:
    """Return whether the configured browser executable is available without launching it."""
    if not settings.browser_enabled:
        return False, "browser automation disabled"

    executable = configured_browser_executable().strip()
    if not executable:
        return False, "browser executable belum dikonfigurasi"

    expanded = Path(executable).expanduser()
    if expanded.parent != Path(".") and expanded.exists() and expanded.is_file():
        return True, str(expanded)

    resolved = shutil.which(executable)
    if resolved:
        return True, resolved
    return False, f"executable '{executable}' tidak ditemukan di PATH"


def validate_browser_runtime() -> None:
    """Fail fast at application startup when browser automation is enabled but unusable."""
    if not settings.browser_enabled:
        return
    available, detail = browser_backend_availability()
    if not available:
        raise BrowserBackendUnavailableError(
            f"Browser automation aktif dengan provider '{settings.browser_backend}', tetapi {detail}. "
            "Install runtime provider atau nonaktifkan BROWSER_ENABLED."
        )


def get_browser_backend() -> BrowserBackend:
    name = _normalized_backend_name()
    if name in {"agent-browser", "agentbrowser"}:
        return agent_browser_backend
    if name in {"ego", "ego-lite", "egolite"}:
        return ego_lite_backend
    raise BrowserBackendUnavailableError(
        f"Browser backend '{settings.browser_backend}' tidak dikenal. Gunakan 'agent-browser' atau 'ego-lite'."
    )
