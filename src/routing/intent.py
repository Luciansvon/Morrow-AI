import re
from typing import ClassVar

from src.core.types import MessageIntent


class IntentDetector:
    """Detektor niat pesan pengguna (Social, Work Request, Question, Command)."""

    SOCIAL_PATTERNS: ClassVar[list[str]] = [
        r"\b(halo|hai|hey|hei|hola)\b",
        r"\b(selamat\s+)?(pagi|siang|sore|malam)\b",
        r"\b(apa kabar|gimana kabarnya|kalian gimana|lagi apa|lagi ngapain)\b",
        r"\b(semua siap|semua ada|hadir\??|standby\??)\b",
        r"\b(makasih|terima\s*kasih|thanks|thx|mantap|gokil)\b",
    ]

    SOCIAL_QUESTION_PATTERNS: ClassVar[list[str]] = [
        r"\b(apa kabar|gimana kabarnya|kalian gimana|lagi apa|lagi ngapain)\b",
        r"\b(semua siap|semua ada|hadir|standby)\b",
    ]

    WORK_ACTION_PATTERNS: ClassVar[list[str]] = [
        (
            r"\b(hitung|cek|analisis|buat|susun|bantu|evaluasi|baca|rangkum|hapus|"
            r"bandingkan|kerjakan|tinjau|jadwalkan|prioritas|launch|strategi|audit|riset|"
            r"cari|nilai|beri|kasih|perbaiki|fix|debug|uji|test)\b"
        ),
    ]

    QUESTION_WORDS: ClassVar[list[str]] = [
        "apakah",
        "bagaimana",
        "berapa",
        "kapan",
        "kenapa",
        "mengapa",
        "siapa",
        "dimana",
        "di mana",
    ]

    LAUGHTER_MARKERS: ClassVar[tuple[str, ...]] = ("wkwk", "kwkw", "haha", "hehe")

    CONTROL_LEAD: ClassVar[str] = (
        r"^\s*(?:(?:manager|marketing|advisor)\s*[,;:]?\s*)?"
        r"(?:(?:makasih|terima\s*kasih|thanks|thx)\s*[,;:]?\s*)?"
        r"(?:tolong\s+)?"
    )
    CONTROL_PATTERNS: ClassVar[tuple[tuple[str, tuple[str, ...]], ...]] = (
        (
            "cancel",
            (
                r"^\s*/(?:cancel|stop)(?:@\w+)?\s*$",
                CONTROL_LEAD + r"(?:stop|berhenti|hentikan|batalkan)\b.*$",
                CONTROL_LEAD + r"batal(?:\s+aja)?\b.*$",
                CONTROL_LEAD + r"jangan\s+(?:di)?lanjut(?:kan)?\b.*$",
                CONTROL_LEAD + r"jangan\s+diteruskan\b.*$",
            ),
        ),
        (
            "pause",
            (
                r"^\s*/pause(?:@\w+)?\s*$",
                CONTROL_LEAD + r"(?:jeda|pause|tunda\s+dulu)\b.*$",
            ),
        ),
        (
            "resume",
            (
                r"^\s*/resume(?:@\w+)?\s*$",
                CONTROL_LEAD + r"(?:lanjutkan|resume)\s+(?:task|tugas|otomatisasi)\b.*$",
            ),
        ),
    )

    @classmethod
    def detect_control_command(cls, text: str) -> str | None:
        text_clean = (text or "").strip().lower()
        for action, patterns in cls.CONTROL_PATTERNS:
            if any(re.search(pattern, text_clean) for pattern in patterns):
                return action
        return None

    @classmethod
    def detect_intent(cls, text: str) -> MessageIntent:
        text_clean = text.strip().lower()
        if cls.detect_control_command(text_clean):
            return MessageIntent.COMMAND

        has_work_action = any(re.search(pat, text_clean) for pat in cls.WORK_ACTION_PATTERNS)
        has_laughter = any(marker in text_clean for marker in cls.LAUGHTER_MARKERS)
        has_social = has_laughter or any(
            re.search(pat, text_clean) for pat in cls.SOCIAL_PATTERNS
        )
        is_social_question = any(
            re.search(pat, text_clean) for pat in cls.SOCIAL_QUESTION_PATTERNS
        )
        has_question_signal = text_clean.endswith("?") or any(
            word in text_clean for word in cls.QUESTION_WORDS
        )

        if has_work_action:
            return MessageIntent.WORK_REQUEST
        if is_social_question:
            return MessageIntent.SOCIAL
        if has_question_signal:
            return MessageIntent.QUESTION
        if has_social:
            return MessageIntent.SOCIAL
        return MessageIntent.WORK_REQUEST


intent_detector = IntentDetector()
