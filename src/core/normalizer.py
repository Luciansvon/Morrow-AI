"""Normalisasi pesan masuk, verifikasi whitelist/allowlist, dan deduplikasi event."""


from src.core.config import settings
from src.core.types import NormalizedMessage
from src.storage.sqlite import db


class MessageNormalizer:
    """Komponen normalisasi dan verifikasi awal pesan."""

    @staticmethod
    def check_access(message: NormalizedMessage) -> tuple[bool, str | None]:
        """
        Memverifikasi apakah pengirim dan grup terdaftar dalam whitelist / allowlist.
        Mengembalikan (is_allowed, rejection_reason).
        """
        if not settings.is_user_whitelisted(message.sender_id):
            return False, f"User ID '{message.sender_id}' tidak terdaftar dalam whitelist."

        if not settings.is_group_allowlisted(message.group_id):
            return False, f"Group ID '{message.group_id}' tidak terdaftar dalam group allowlist."

        return True, None

    @staticmethod
    async def is_duplicate_event(event_id: str, platform: str = "telegram") -> bool:
        """
        Memeriksa apakah event_id sudah pernah diproses sebelumnya (AC-021 Deduplication).
        Jika belum, mencatatnya ke database.
        """
        row = await db.fetch_one(
            "SELECT event_id FROM processed_events WHERE event_id = ?",
            (event_id,),
        )
        if row:
            return True  # Duplikat!

        # Catat event baru
        await db.execute(
            "INSERT INTO processed_events (event_id, platform) VALUES (?, ?)",
            (event_id, platform),
        )
        return False
