"""Backend-agnostic browser automation contracts and concrete providers."""

from src.browser.agent_browser import (
    AgentBrowserBackend,
    BrowserBackendUnavailableError,
    agent_browser_backend,
)
from src.browser.base import BrowserActionClass, BrowserBackend

__all__ = [
    "AgentBrowserBackend",
    "BrowserActionClass",
    "BrowserBackend",
    "BrowserBackendUnavailableError",
    "agent_browser_backend",
]
