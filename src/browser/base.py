"""Browser abstraction inspired by task-space ownership, without hard-coding a provider."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class BrowserActionClass(str, Enum):
    READ = "read"
    PREPARE = "prepare"
    COMMIT = "commit"


class BrowserBackend(ABC):
    """Provider-neutral browser contract.

    READ actions inspect or navigate without mutating external state.
    PREPARE actions may alter only the local page/session state, such as filling a draft.
    COMMIT actions submit, purchase, post, delete, send, or otherwise mutate external state
    and MUST pass through Morrow's approval gateway before execution.
    """

    @abstractmethod
    async def open(self, url: str, *, task_space: str) -> dict[str, Any]:
        """Open/reuse a page in an isolated task space."""

    @abstractmethod
    async def snapshot(self, *, task_space: str) -> dict[str, Any]:
        """Return a semantic page snapshot suitable for agent reasoning."""

    @abstractmethod
    async def screenshot(self, *, task_space: str) -> dict[str, Any]:
        """Capture the visible page for visual inspection."""

    @abstractmethod
    async def interact(
        self,
        action: str,
        parameters: dict[str, Any],
        *,
        task_space: str,
        action_class: BrowserActionClass,
    ) -> dict[str, Any]:
        """Perform a browser action after policy/approval classification."""

    @abstractmethod
    async def handoff_to_user(self, *, task_space: str, reason: str) -> dict[str, Any]:
        """Give control to the user for login/captcha/manual review."""

    @abstractmethod
    async def take_back_control(self, *, task_space: str) -> dict[str, Any]:
        """Resume only after explicit user continuation."""
