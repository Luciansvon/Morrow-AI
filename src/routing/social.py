"""Zero-token fast social responses. Rich banter is handled by persona-aware LLM runtime."""

import re

from src.core.types import RoleID

FAST_SOCIAL_RE = re.compile(
    r"^\s*(halo|hai|hey|hei|hola|pagi|siang|sore|malam|selamat\s+(pagi|siang|sore|malam))"
    r"([\s,!?.]*(semua|semuanya|tim|team|guys|teman-teman|kalian))?[\s,!?.]*$",
    re.IGNORECASE,
)

SOCIAL_RESPONSES = {
    RoleID.MANAGER: {
        "default": "Ada, Bos. Kenapa?",
        "pagi": "Pagi, Bos. Gue ada. Mau beresin apa dulu?",
        "siang": "Siang. Ada apa, Bos?",
        "sore": "Sore, Bos. Masih nyala kok wkwk.",
        "malam": "Malam. Gue ada, santai aja.",
    },
    RoleID.MARKETING: {
        "default": "hadir 😭 ada apaan?",
        "pagi": "pagiii, hadir. ada yang mau dibedah?",
        "siang": "siang, gue ada. apaan nih?",
        "sore": "soreee. masih hidup, tenang 😭",
        "malam": "malam. masih online, sayangnya 😭",
    },
    RoleID.ADVISOR: {
        "default": "Ada. Mau bahas apa?",
        "pagi": "Pagi. Saya ada, mau cek apa dulu?",
        "siang": "Siang. Ada yang perlu ditimbang?",
        "sore": "Sore. Masih ada, belum pensiun rupanya.",
        "malam": "Malam. Saya masih di sini, mau bahas apa?",
    },
}


def is_fast_social(text: str = "") -> bool:
    return bool(FAST_SOCIAL_RE.match(text or ""))


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
