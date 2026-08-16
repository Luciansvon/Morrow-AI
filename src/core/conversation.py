"""Task-local conversation continuity metadata shared between runtime and channel sender."""

from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(frozen=True)
class ConversationExecutionContext:
    thread_id: str | None
    task_id: str | None
    root_user_text: str


_current_context: ContextVar[ConversationExecutionContext | None] = ContextVar(
    "morrow_conversation_execution_context",
    default=None,
)


def set_conversation_context(
    *,
    thread_id: str | None,
    task_id: str | None,
    root_user_text: str,
) -> None:
    _current_context.set(
        ConversationExecutionContext(
            thread_id=thread_id,
            task_id=task_id,
            root_user_text=(root_user_text or "").strip(),
        )
    )


def get_conversation_context() -> ConversationExecutionContext | None:
    return _current_context.get()


def clear_conversation_context() -> None:
    _current_context.set(None)
