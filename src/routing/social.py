"""Zero-token fast social responses. Rich banter is handled by persona-aware LLM runtime."""

import re

from src.core.types import RoleID

ROLE_PREFIX_RE = re.compile(
    r"^\s*(?:(?:manager|marketing|advisor)"
    r"(?:\s*(?:dan|&|,)\s*(?:manager|marketing|advisor))*)\s*,?\s*",
    re.IGNORECASE,
)

FAST_SOCIAL_RE = re.compile(
    r"^\s*(halo|hai|hey|hei|hola|pagi|siang|sore|malam|selamat\s+(pagi|siang|sore|malam))"
    r"([\s,!?.]*(semua|semuanya|tim|team|guys|teman-teman|kalian))?[\s,!?.]*$",
    re.IGNORECASE,
)

SOCIAL_RESPONSES = {
    RoleID.MANAGER: {
        "default": "Ada, Bos. Mau putuskan atau rapihin prioritas apa dulu?",
        "pagi": "Pagi, Bos. Gue ada. Prioritas dan arah kerja pertama hari ini apa?",
        "siang": "Siang. Ada, Bos. Apa yang perlu diputuskan?",
        "sore": "Sore. Masih jalan. Ada prioritas yang perlu diberesin sebelum hari selesai?",
        "malam": "Malam. Gue ada. Kalau penting, kita bikin next step dan prioritasnya jelas dulu.",
    },
    RoleID.MARKETING: {
        "default": "Marketing ada. Mau bongkar audience, angle, atau eksperimen apa?",
        "pagi": "Pagi. Marketing ada. Mau ngetes hipotesis apa biar orang berhenti scroll?",
        "siang": "Siang. Marketing ada. Lagi cari angle atau data yang perlu diuji?",
        "sore": "Sore. Marketing masih ada. Mau cek apa yang benar-benar ngaruh ke metric?",
        "malam": "Malam. Marketing ada. Ide boleh liar, metric tetap harus waras.",
    },
    RoleID.ADVISOR: {
        "default": "Ada. Mau lihat keputusan ini arahnya ke mana dan risiko apa yang ikut terbawa?",
        "pagi": "Pagi. Saya ada. Mau cek risiko, peluang, dan blind spot apa dulu?",
        "siang": "Siang. Ada risiko yang perlu dilihat dari sisi customer atau jangka panjang?",
        "sore": "Sore. Saya ada. Mari cek risiko dan konsekuensi yang belum kelihatan.",
        "malam": "Malam. Saya masih di sini. Mau timbang arah dan risikonya?",
    },
}


def is_fast_social(text: str = "") -> bool:
    normalized = ROLE_PREFIX_RE.sub("", text or "", count=1)
    return bool(FAST_SOCIAL_RE.match(normalized))


def social_response(role: RoleID, text: str = "") -> str:
    lower = (text or "").lower()
    if "pagi" in lower:
        return SOCIAL_RESPONSES[role]["pagi"]
    if "siang" in lower:
        return SOCIAL_RESPONSES[role]["siang"]
    if "sore" in lower:
        return SOCIAL_RESPONSES[role]["sore"]
    if "malam" in lower:
        return SOCIAL_RESPONSES[role]["malam"]
    return SOCIAL_RESPONSES[role]["default"]
