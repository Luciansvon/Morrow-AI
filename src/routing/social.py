"""Zero-token social responses dengan gaya bicara per role."""

from src.core.types import RoleID

SOCIAL_RESPONSES = {
    RoleID.MANAGER: {
        "default": "Halo Bos. Manager standby, siap rapihin prioritas dan langkah berikutnya.",
        "pagi": "Pagi Bos. Manager siap rapihin prioritas biar arah kerja hari ini jelas.",
        "siang": "Siang Bos. Manager standby, kita cek progres dan beresin yang paling penting dulu.",
        "sore": "Sore Bos. Manager siap review progres dan kunci next step-nya.",
        "malam": "Malam Bos. Manager standby, kita rapihin sisa kerjaan tanpa bikin langkah baru berantakan.",
    },
    RoleID.MARKETING: {
        "default": "Halo Bos. Marketing hadir, siap cari angle, ide, atau copy yang paling nendang.",
        "pagi": "Pagi Bos. Marketing siap cari angle yang bikin orang berhenti scroll.",
        "siang": "Siang Bos. Marketing standby, siap poles pesan biar lebih kena ke target.",
        "sore": "Sore Bos. Marketing siap bedah hasil dan cari cara biar campaign-nya makin ngangkat.",
        "malam": "Malam Bos. Marketing masih standby, siap matengin ide sebelum dilempar ke audience.",
    },
    RoleID.ADVISOR: {
        "default": "Halo Bos. Advisor standby, siap bedah risiko dan bantu pilih langkah paling aman.",
        "pagi": "Pagi Bos. Advisor siap cek risiko dulu sebelum kita gas.",
        "siang": "Siang Bos. Advisor standby, siap timbang opsi dan dampaknya satu per satu.",
        "sore": "Sore Bos. Advisor siap review keputusan hari ini dan tandai celah yang masih rawan.",
        "malam": "Malam Bos. Advisor standby, siap bantu pastikan keputusan besok nggak nyisain risiko tersembunyi.",
    },
}


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
