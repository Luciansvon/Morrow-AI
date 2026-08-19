"""Request-scoped identity carried through Morrow async execution.

This context is convenience plumbing only. Authorization remains enforced by Morrow Core and the
storage/integration boundary must still validate the supplied scope before mutating or returning data.
"""

from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(frozen=True)
class RequestIdentity:
    user_id: str
    group_id: str
    platform: str


_identity: ContextVar[RequestIdentity | None] = ContextVar(
    "morrow_request_identity",
    default=None,
)


def set_request_identity(user_id: str, group_id: str, platform: str) -> RequestIdentity:
    identity = RequestIdentity(
        user_id=str(user_id),
        group_id=str(group_id),
        platform=str(platform),
    )
    _identity.set(identity)
    return identity


def get_request_identity() -> RequestIdentity | None:
    return _identity.get()


def current_user_id() -> str | None:
    identity = get_request_identity()
    return identity.user_id if identity else None


def current_group_id() -> str | None:
    identity = get_request_identity()
    return identity.group_id if identity else None
