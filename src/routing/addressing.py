import re
from typing import ClassVar

from src.core.types import (
    AddressingResult,
    AddressingType,
    MessageIntent,
    NormalizedMessage,
    RoleID,
)
from src.routing.intent import intent_detector


class AddressingDetector:
    """Detektor pengalamatan percakapan cerdas membedakan sapaan kolektif vs quantifier objek."""

    # Istilah sapaan kolektif tim
    COLLECTIVE_VOCATIVE_PATTERNS: ClassVar[list[str]] = [
        r"^(halo|hai|hey|hei|pagi|siang|sore|malam|selamat\s+\w+)\s+(semua|semuanya|tim|team|guys|teman-teman|kalian)\b",
        r"\b(apa\s+kabar|gimana\s+kabarnya)\s+(semua|semuanya|tim|team|guys|teman-teman|kalian)\b",
        r"^(kalian|kalian\s+semua|semua\s+orang)\s+(gimana|ada|siap|lagi\s+apa|dengerin|tolong)\b",
        r"^(semua|semuanya|tim|team)\s*,\s*",
        r"\b(semua\s+siap|semua\s+ada|tim\s+siap|tim\s+standby)\b",
        r"^(semua|semuanya)\s+(siap|ada|dengerin|tolong\s+dengar)\b",
    ]

    # Pola penunjuk kuantitas objek (Object Quantifiers - BUKAN sapaan agen)
    OBJECT_QUANTIFIER_PATTERNS: ClassVar[list[str]] = [
        # Kata kerja tindakan + semua/semuanya + objek non-agen
        r"\b(hitung|cek|analisis|baca|rangkum|hapus|bandingkan|periksa|ubah|revisi)\s+(semua|semuanya)\b",
        # semua + objek non-agen (harga, produk, file, task, campaign, data, hasil)
        r"\bsemua\s+(harga|produk|file|berkas|task|tugas|campaign|kampanye|data|hasil|dokumen|gambar|transaksi|nominal|pesan)\b",
        # semua + predikat objek (semua harga ini salah, semua produk mahal)
        r"\bsemua\s+\w+\s+(ini\s+)?(mahal|murah|salah|rusak|naik|turun|kurang|lebih|error|bug|batal)\b",
    ]

    @classmethod
    async def detect(cls, message: NormalizedMessage) -> AddressingResult:
        text_lower = message.text.strip().lower()
        intent = intent_detector.detect_intent(message.text)

        # 1. Cek Pola Quantifier Objek yang JELAS BUKAN sapaan agen
        is_object_quantifier = any(re.search(pat, text_lower) for pat in cls.OBJECT_QUANTIFIER_PATTERNS)
        is_collective_vocative = any(re.search(pat, text_lower) for pat in cls.COLLECTIVE_VOCATIVE_PATTERNS)

        if is_object_quantifier and not is_collective_vocative:
            return AddressingResult(
                addressing_type=AddressingType.NONE,
                target_agents=[],
                intent=intent,
                allow_multi_response=False,
                requires_coordinator=False,
                confidence=0.99,
            )

        # 2. Cek Sebutan Nama Peran Eksplisit (Single atau Multiple Agents)
        mentioned_roles: list[RoleID] = []
        for role in [RoleID.MANAGER, RoleID.MARKETING, RoleID.ADVISOR]:
            # Cari sebutan peran (contoh: "manager", "@marketing", "advisor")
            pat = rf"@?{role.value}\b"
            if re.search(pat, text_lower):
                if role not in mentioned_roles:
                    mentioned_roles.append(role)

        # Jika ada 3 peran disebut secara bersamaan (misal: "Manager, Marketing, Advisor, tolong...")
        if len(mentioned_roles) == 3:
            return AddressingResult(
                addressing_type=AddressingType.ALL_AGENTS,
                target_agents=[RoleID.MANAGER, RoleID.MARKETING, RoleID.ADVISOR],
                intent=intent,
                allow_multi_response=(intent == MessageIntent.SOCIAL),
                requires_coordinator=(intent != MessageIntent.SOCIAL),
                coordinator=RoleID.MANAGER if intent != MessageIntent.SOCIAL else None,
                confidence=0.98,
            )

        # Jika ada 2 peran disebut (misal: "Manager dan Marketing, halo" atau "Manager dan Advisor, evaluasi...")
        if len(mentioned_roles) == 2:
            return AddressingResult(
                addressing_type=AddressingType.MULTIPLE_AGENTS,
                target_agents=mentioned_roles,
                intent=intent,
                allow_multi_response=(intent == MessageIntent.SOCIAL),
                requires_coordinator=(intent != MessageIntent.SOCIAL),
                coordinator=mentioned_roles[0] if intent != MessageIntent.SOCIAL else None,
                confidence=0.98,
            )

        # Jika tepat 1 peran disebut (misal: "Manager, halo")
        if len(mentioned_roles) == 1:
            return AddressingResult(
                addressing_type=AddressingType.SINGLE_AGENT,
                target_agents=mentioned_roles,
                intent=intent,
                allow_multi_response=False,
                requires_coordinator=False,
                coordinator=mentioned_roles[0],
                confidence=0.99,
            )

        # 3. Cek Sapaan Kolektif Tim ("halo semua", "pagi tim", "kalian gimana?", "semua, bantu launch")
        if is_collective_vocative:
            is_social = (intent == MessageIntent.SOCIAL)
            return AddressingResult(
                addressing_type=AddressingType.ALL_AGENTS,
                target_agents=[RoleID.MANAGER, RoleID.MARKETING, RoleID.ADVISOR],
                intent=intent,
                allow_multi_response=is_social,
                requires_coordinator=not is_social,
                coordinator=RoleID.MANAGER if not is_social else None,
                confidence=0.98,
            )

        # 4. Default: Bukan pengalamatan multi-agen eksplisit (Teruskan ke Normal Role Router)
        return AddressingResult(
            addressing_type=AddressingType.NONE,
            target_agents=[],
            intent=intent,
            allow_multi_response=False,
            requires_coordinator=False,
            confidence=0.95,
        )


addressing_detector = AddressingDetector()
