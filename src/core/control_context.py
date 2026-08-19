"""Request-local target metadata for stop/pause/resume control commands."""

from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(frozen=True)
class ControlTarget:
    action: str
    task_id: str | None = None


_target: ContextVar[ControlTarget | None] = ContextVar("morrow_control_target", default=None)


def set_control_target(action: str | None, task_id: str | None = None) -> None:
    _target.set(ControlTarget(action=action, task_id=task_id) if action else None)


def get_control_target(action: str | None = None) -> ControlTarget | None:
    target = _target.get()
    if target is None:
        return None
    if action is not None and target.action != action:
        return None
    return target
