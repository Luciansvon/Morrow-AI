"""Access control dan deduplikasi event masuk."""

from src.core.config import settings
from src.core.types import NormalizedMessage
from src.storage.sqlite import db


class MessageNormalizer:
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

    @staticmethod
    async def claim_event(event_id: str, platform: str = "telegram", group_id: str | None = None) -> bool:
        """Atomic claim. True berarti caller memenangkan event dan boleh memprosesnya."""
        canonical = MessageNormalizer.canonical_event_id(event_id, platform, group_id)
        conn = await db.connect()
        cursor = await conn.execute(
            "INSERT OR IGNORE INTO processed_events (event_id, platform, group_id) VALUES (?, ?, ?)",
            (canonical, platform, group_id),
        )
        await conn.commit()
        return cursor.rowcount == 1

    @staticmethod
    async def is_duplicate_event(event_id: str, platform: str = "telegram", group_id: str | None = None) -> bool:
        return not await MessageNormalizer.claim_event(event_id, platform, group_id)
