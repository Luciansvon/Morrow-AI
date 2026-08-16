"""Browser provider selection behind Morrow's provider-neutral contract."""

from src.browser.agent_browser import agent_browser_backend
from src.browser.base import BrowserBackend, BrowserBackendUnavailableError
from src.browser.ego_lite import ego_lite_backend
from src.core.config import settings


def get_browser_backend() -> BrowserBackend:
    name = settings.browser_backend.strip().lower().replace("_", "-")
    if name in {"ego", "ego-lite", "egolite"}:
        return ego_lite_backend
    if name in {"agent-browser", "agentbrowser"}:
        return agent_browser_backend
    raise BrowserBackendUnavailableError(
        f"Browser backend '{settings.browser_backend}' tidak dikenal. Gunakan 'ego-lite' atau 'agent-browser'."
    )
