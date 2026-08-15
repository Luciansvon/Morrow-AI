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
        "default": "Ada, Bos. Mau rapihin prioritas apa dulu?",
        "pagi": "Pagi, Bos. Gue ada. Mau rapihin arah kerja hari ini?",
        "siang": "Siang. Ada apa, Bos?",
        "sore": "Sore, Bos. Masih nyala kok wkwk.",
        "malam": "Malam. Gue ada, santai aja.",
    },
    RoleID.MARKETING: {
        "default": "Marketing hadir 😭 ada apaan?",
        "pagi": "pagiii. Marketing hadir, ada yang mau bikin orang berhenti scroll?",
        "siang": "siang, Marketing ada. apaan nih?",
        "sore": "soreee. Marketing masih hidup, tenang 😭",
        "malam": "malam. Marketing masih online, sayangnya 😭",
    },
    RoleID.ADVISOR: {
        "default": "Ada. Mau bahas apa? Kalau perlu saya cek risikonya sekalian.",
        "pagi": "Pagi. Saya ada. Mau cek risiko apa dulu?",
        "siang": "Siang. Ada yang perlu ditimbang risikonya?",
        "sore": "Sore. Masih ada, belum pensiun rupanya. Ada risiko yang perlu dicek?",
        "malam": "Malam. Saya masih di sini. Mau bahas risiko apa?",
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
