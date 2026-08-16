"""Backend-agnostic browser automation contracts and concrete providers."""

from src.browser.agent_browser import AgentBrowserBackend, agent_browser_backend
from src.browser.base import BrowserActionClass, BrowserBackend, BrowserBackendUnavailableError
from src.browser.ego_lite import EgoLiteBackend, ego_lite_backend
from src.browser.provider import get_browser_backend

__all__ = [
    "AgentBrowserBackend",
    "BrowserActionClass",
    "BrowserBackend",
    "BrowserBackendUnavailableError",
    "EgoLiteBackend",
    "agent_browser_backend",
    "ego_lite_backend",
    "get_browser_backend",
]
