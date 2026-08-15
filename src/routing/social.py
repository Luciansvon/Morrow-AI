"""Zero-token social responses untuk greeting yang jelas."""

from src.core.types import RoleID


SOCIAL_RESPONSES = {
    RoleID.MANAGER: "Halo Bos, siap.",
    RoleID.MARKETING: "Halo Bos, siap.",
    RoleID.ADVISOR: "Halo Bos, siap.",
}


def social_response(role: RoleID, text: str = "") -> str:
    lower = (text or "").lower()
    if "pagi" in lower:
        return "Selamat pagi Bos, siap."
    if "siang" in lower:
        return "Selamat siang Bos, siap."
    if "sore" in lower:
        return "Selamat sore Bos, siap."
    if "malam" in lower:
        return "Selamat malam Bos, siap."
    return SOCIAL_RESPONSES[role]
