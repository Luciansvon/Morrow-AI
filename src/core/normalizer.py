"""Access control dan durable event deduplication/lifecycle."""

import asyncio
import time
import uuid
from contextvars import ContextVar

from src.core.config import settings
from src.core.types import NormalizedMessage
from src.storage.sqlite import db


class MessageNormalizer:
    EVENT_LEASE_SECONDS = 1800.0
    EVENT_WAIT_POLL_SECONDS = 0.25
    _claim_context: ContextVar[tuple[str, str] | None] = ContextVar(
        "morrow_event_claim_context",
        default=None,
    )

    @staticmethod
    def check_access(message: NormalizedMessage) -> tuple[bool, str | None]:
        if message.platform == "cli" and settings.morrow_env.lower() != "production":
            return True, None
        if not settings.is_user_whitelisted(message.sender_id):
            return False, f"User ID '{message.sender_id}' tidak terdaftar dalam whitelist."
        if not settings.is_group_allowlisted(message.group_id):
            return False, f"Group ID '{message.group_id}' tidak terdaftar dalam group allowlist."
        return True, None

    @staticmethod
    def canonical_event_id(event_id: str, platform: str = "telegram", group_id: str | None = None) -> str:
        if group_id is None:
            return str(event_id)
        return f"{platform}:{group_id}:{event_id}"

    @classmethod
    def _context_owner_token(cls, canonical: str) -> str | None:
        claim = cls._claim_context.get()
        if claim and claim[0] == canonical:
            return claim[1]
        return None

    @classmethod
    async def claim_event_owned(
        cls,
        event_id: str,
        platform: str = "telegram",
        group_id: str | None = None,
    ) -> str | None:
        """Atomically claim an event and return the durable lease owner token.

        A reclaimed attempt always receives a new token. The token is retained in this async
        context so existing callers of `mark_event_*` automatically close only their own lease.
        """
        canonical = cls.canonical_event_id(event_id, platform, group_id)
        now = time.time()
        lease_until = now + cls.EVENT_LEASE_SECONDS
        owner_token = f"evt_{uuid.uuid4().hex}"
        async with db.transaction() as conn:
            cursor = await conn.execute(
                """SELECT status, attempt_count, lease_until
                   FROM processed_events WHERE event_id=?""",
                (canonical,),
            )
            raw = await cursor.fetchone()
            if not raw:
                await conn.execute(
                    """INSERT INTO processed_events
                       (event_id, platform, group_id, status, attempt_count, lease_until,
                        owner_token, last_error, updated_at)
                       VALUES (?, ?, ?, 'processing', 1, ?, ?, NULL, CURRENT_TIMESTAMP)""",
                    (canonical, platform, group_id, lease_until, owner_token),
                )
                cls._claim_context.set((canonical, owner_token))
                return owner_token

            row = dict(raw)
            status = str(row.get("status") or "completed")
            if status == "completed":
                return None
            current_lease = float(row.get("lease_until") or 0.0)
            if status == "processing" and current_lease > now:
                return None

            updated = await conn.execute(
                """UPDATE processed_events
                   SET status='processing', attempt_count=COALESCE(attempt_count, 0)+1,
                       lease_until=?, owner_token=?, last_error=NULL,
                       updated_at=CURRENT_TIMESTAMP
                   WHERE event_id=? AND status!='completed'
                     AND (status!='processing' OR COALESCE(lease_until, 0)<=?)""",
                (lease_until, owner_token, canonical, now),
            )
            if updated.rowcount == 1:
                cls._claim_context.set((canonical, owner_token))
                return owner_token
            return None

    @classmethod
    async def claim_event(
        cls,
        event_id: str,
        platform: str = "telegram",
        group_id: str | None = None,
    ) -> bool:
        """Compatibility wrapper returning only whether the claim succeeded."""
        return await cls.claim_event_owned(event_id, platform, group_id) is not None

    @classmethod
    async def mark_event_completed(
        cls,
        event_id: str,
        platform: str = "telegram",
        group_id: str | None = None,
        owner_token: str | None = None,
    ) -> bool:
        canonical = cls.canonical_event_id(event_id, platform, group_id)
        effective_owner = owner_token or cls._context_owner_token(canonical)
        if effective_owner is None:
            return False
        cursor = await db.execute(
            """UPDATE processed_events
               SET status='completed', lease_until=NULL, owner_token=NULL, last_error=NULL,
                   updated_at=CURRENT_TIMESTAMP
               WHERE event_id=? AND status='processing' AND owner_token=?""",
            (canonical, effective_owner),
        )
        return cursor.rowcount == 1

    @classmethod
    async def mark_event_failed(
        cls,
        event_id: str,
        platform: str = "telegram",
        group_id: str | None = None,
        error: str | None = None,
        owner_token: str | None = None,
    ) -> bool:
        canonical = cls.canonical_event_id(event_id, platform, group_id)
        safe_error = (error or "processing_failed")[:1000]
        effective_owner = owner_token or cls._context_owner_token(canonical)
        if effective_owner is None:
            return False
        cursor = await db.execute(
            """UPDATE processed_events
               SET status='failed', lease_until=NULL, owner_token=NULL, last_error=?,
                   updated_at=CURRENT_TIMESTAMP
               WHERE event_id=? AND status='processing' AND owner_token=?""",
            (safe_error, canonical, effective_owner),
        )
        return cursor.rowcount == 1

    @classmethod
    async def wait_for_event_retry(
        cls,
        event_id: str,
        platform: str = "telegram",
        group_id: str | None = None,
        timeout_seconds: float | None = None,
    ) -> bool:
        """Wait behind another bot's claim and return True only when takeover is safe."""
        canonical = cls.canonical_event_id(event_id, platform, group_id)
        timeout = cls.EVENT_LEASE_SECONDS if timeout_seconds is None else max(0.0, timeout_seconds)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            row = await db.fetch_one(
                "SELECT status, lease_until FROM processed_events WHERE event_id=?",
                (canonical,),
            )
            if not row:
                return True
            status = str(row.get("status") or "completed")
            if status == "completed":
                return False
            if status == "failed":
                return True
            if status == "processing" and float(row.get("lease_until") or 0.0) <= time.time():
                return True
            await asyncio.sleep(cls.EVENT_WAIT_POLL_SECONDS)
        return False

    @staticmethod
    async def is_duplicate_event(event_id: str, platform: str = "telegram", group_id: str | None = None) -> bool:
        return not await MessageNormalizer.claim_event(event_id, platform, group_id)
