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
        "default": "Ada, Bos. Mau putuskan atau beresin apa dulu?",
        "pagi": "Pagi, Bos. Gue ada. Prioritas pertama hari ini apa?",
        "siang": "Siang. Ada, Bos. Apa yang perlu diputuskan?",
        "sore": "Sore. Masih jalan. Ada yang perlu diberesin sebelum hari selesai?",
        "malam": "Malam. Gue ada. Kalau penting, kita bikin next step-nya jelas dulu.",
    },
    RoleID.MARKETING: {
        "default": "Ada. Mau bongkar audience, angle, atau eksperimen apa?",
        "pagi": "Pagi. Marketing ada. Mau ngetes hipotesis apa hari ini?",
        "siang": "Siang. Ada. Lagi cari angle atau data yang perlu diuji?",
        "sore": "Sore. Masih ada. Mau cek apa yang benar-benar ngaruh ke metric?",
        "malam": "Malam. Marketing ada. Ide boleh liar, metric tetap harus waras.",
    },
    RoleID.ADVISOR: {
        "default": "Ada. Mau lihat keputusan ini arahnya ke mana?",
        "pagi": "Pagi. Saya ada. Mau cek peluang dan blind spot apa dulu?",
        "siang": "Siang. Ada yang perlu dilihat dari sisi customer atau jangka panjang?",
        "sore": "Sore. Saya ada. Mari cek apakah ada konsekuensi yang belum kelihatan.",
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
