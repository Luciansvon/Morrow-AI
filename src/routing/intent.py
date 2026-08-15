import re
from typing import ClassVar

from src.core.types import MessageIntent


class IntentDetector:
    """Detektor niat pesan pengguna (Social, Work Request, Question, Command)."""

    # Pola sapaan sosial deterministik
    SOCIAL_PATTERNS: ClassVar[list[str]] = [
        r"\b(halo|hai|hey|hei|hola)\b",
        r"\b(selamat\s+)?(pagi|siang|sore|malam)\b",
        r"\b(apa kabar|gimana kabarnya|kalian gimana|lagi apa)\b",
        r"\b(semua siap|semua ada|hadir\??|standby\??)\b",
    ]

    # Kata kerja tindakan kerja (Work Request / Command)
    WORK_ACTION_PATTERNS: ClassVar[list[str]] = [
        r"\b(hitung|cek|analisis|buat|susun|bantu|evaluasi|baca|rangkum|hapus|bandingkan|kerjakan|tinjau|jadwalkan|prioritas|launch|strategi)\b",
    ]

    @classmethod
    def detect_intent(cls, text: str) -> MessageIntent:
        text_clean = text.strip().lower()

        # 1. Cek pola tindakan kerja terlebih dahulu (jika ada instruksi tugas kerja eksplisit)
        # Contoh: "semua, tolong hitung ini" -> work_request
        # Tapi jika cuma "semua siap?" atau "halo semua" -> social
        has_work_action = any(re.search(pat, text_clean) for pat in cls.WORK_ACTION_PATTERNS)
        has_social = any(re.search(pat, text_clean) for pat in cls.SOCIAL_PATTERNS)

        if has_social and not has_work_action:
            return MessageIntent.SOCIAL

        if has_work_action:
            return MessageIntent.WORK_REQUEST

        if has_social:
            return MessageIntent.SOCIAL

        if text_clean.endswith("?") or any(w in text_clean for w in ["apakah", "bagaimana", "berapa", "kapan", "kenapa"]):
            return MessageIntent.QUESTION

        return MessageIntent.WORK_REQUEST


intent_detector = IntentDetector()
