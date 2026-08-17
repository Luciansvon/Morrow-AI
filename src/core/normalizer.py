"""Access control dan durable event deduplication/lifecycle."""

import asyncio
import time

from src.core.config import settings
from src.core.types import NormalizedMessage
from src.storage.sqlite import db


class MessageNormalizer:
    EVENT_LEASE_SECONDS = 1800.0
    EVENT_WAIT_POLL_SECONDS = 0.25

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
    async def claim_event(
        cls,
        event_id: str,
        platform: str = "telegram",
        group_id: str | None = None,
    ) -> bool:
        """Atomically claim an event for processing.

        Completed events stay deduplicated. Failed events and abandoned processing leases may
        be reclaimed, avoiding the old at-most-once behavior where a crash after claim could
        permanently discard a Telegram update.
        """
        canonical = cls.canonical_event_id(event_id, platform, group_id)
        now = time.time()
        lease_until = now + cls.EVENT_LEASE_SECONDS
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
                        last_error, updated_at)
                       VALUES (?, ?, ?, 'processing', 1, ?, NULL, CURRENT_TIMESTAMP)""",
                    (canonical, platform, group_id, lease_until),
                )
                return True

            row = dict(raw)
            status = str(row.get("status") or "completed")
            if status == "completed":
                return False
            current_lease = float(row.get("lease_until") or 0.0)
            if status == "processing" and current_lease > now:
                return False

            updated = await conn.execute(
                """UPDATE processed_events
                   SET status='processing', attempt_count=COALESCE(attempt_count, 0)+1,
                       lease_until=?, last_error=NULL, updated_at=CURRENT_TIMESTAMP
                   WHERE event_id=? AND status!='completed'""",
                (lease_until, canonical),
            )
            return updated.rowcount == 1

    @classmethod
    async def mark_event_completed(
        cls,
        event_id: str,
        platform: str = "telegram",
        group_id: str | None = None,
    ) -> None:
        canonical = cls.canonical_event_id(event_id, platform, group_id)
        await db.execute(
            """UPDATE processed_events
               SET status='completed', lease_until=NULL, last_error=NULL,
                   updated_at=CURRENT_TIMESTAMP
               WHERE event_id=?""",
            (canonical,),
        )

    @classmethod
    async def mark_event_failed(
        cls,
        event_id: str,
        platform: str = "telegram",
        group_id: str | None = None,
        error: str | None = None,
    ) -> None:
        canonical = cls.canonical_event_id(event_id, platform, group_id)
        safe_error = (error or "processing_failed")[:1000]
        await db.execute(
            """UPDATE processed_events
               SET status='failed', lease_until=NULL, last_error=?,
                   updated_at=CURRENT_TIMESTAMP
               WHERE event_id=? AND status='processing'""",
            (safe_error, canonical),
        )

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
