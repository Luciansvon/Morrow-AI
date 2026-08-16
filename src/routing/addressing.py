import re
from typing import ClassVar

from src.adapters.telegram.bot_registry import bot_registry
from src.core.types import (
    AddressingResult,
    AddressingType,
    MessageIntent,
    NormalizedMessage,
    RoleID,
)
from src.routing.intent import intent_detector
from src.storage.sqlite import db


class AddressingDetector:
    """Bedakan explicit agent address, collective vocative, dan object quantifier."""

    COLLECTIVE_VOCATIVE_PATTERNS: ClassVar[list[str]] = [
        (
            r"^(halo|hai|hey|hei|pagi|siang|sore|malam|selamat\s+\w+)\s+"
            r"(semua|semuanya|tim|team|guys|teman-teman|kalian)\b"
        ),
        (
            r"\b(apa\s+kabar|gimana\s+kabarnya)\s+"
            r"(semua|semuanya|tim|team|guys|teman-teman|kalian)\b"
        ),
        (
            r"^(kalian|kalian\s+semua|semua\s+orang)\s+"
            r"(gimana|ada|siap|lagi\s+apa|dengerin|tolong)\b"
        ),
        r"^(semua|semuanya|tim|team)\s*,\s*",
        r"\b(semua\s+siap|semua\s+ada|tim\s+siap|tim\s+standby)\b",
        r"^(semua|semuanya)\s+(siap|ada|dengerin|tolong\s+dengar)\b",
    ]

    OBJECT_QUANTIFIER_PATTERNS: ClassVar[list[str]] = [
        (
            r"\b(hitung|cek|analisis|baca|rangkum|hapus|bandingkan|periksa|ubah|revisi)\s+"
            r"(semua|semuanya)\b"
        ),
        (
            r"\bsemua\s+(harga|produk|file|berkas|task|tugas|campaign|kampanye|data|hasil|"
            r"dokumen|gambar|transaksi|nominal|pesan)\b"
        ),
        (
            r"\bsemua\s+\w+\s+(ini\s+)?"
            r"(mahal|murah|salah|rusak|naik|turun|kurang|lebih|error|bug|batal)\b"
        ),
    ]

    @staticmethod
    async def _explicit_roles(text_lower: str) -> list[RoleID]:
        rows = await db.fetch_all("SELECT role_id, display_name FROM agents")
        display_names = {row["role_id"]: row["display_name"] for row in rows}
        mentioned: list[RoleID] = []
        for role in (RoleID.MANAGER, RoleID.MARKETING, RoleID.ADVISOR):
            terms = {role.value}
            display_name = str(display_names.get(role.value, "")).strip().lower()
            if display_name:
                terms.add(display_name)
            patterns = [
                rf"(?<!\w)@?{re.escape(term)}(?!\w)"
                for term in terms
            ]
            username = bot_registry.get_username(role)
            if username:
                patterns.append(rf"(?<!\w)@{re.escape(username.lower())}(?!\w)")
            if any(re.search(pattern, text_lower) for pattern in patterns):
                mentioned.append(role)
        return mentioned

    @staticmethod
    def _work_coordinator(mentioned_roles: list[RoleID]) -> RoleID:
        """Manager owns operational coordination whenever explicitly included."""
        if RoleID.MANAGER in mentioned_roles:
            return RoleID.MANAGER
        return mentioned_roles[0]

    @staticmethod
    def _result_for_explicit(
        mentioned_roles: list[RoleID],
        intent: MessageIntent,
    ) -> AddressingResult:
        if len(mentioned_roles) == 3:
            return AddressingResult(
                addressing_type=AddressingType.ALL_AGENTS,
                target_agents=mentioned_roles,
                intent=intent,
                allow_multi_response=intent == MessageIntent.SOCIAL,
                requires_coordinator=intent != MessageIntent.SOCIAL,
                coordinator=RoleID.MANAGER if intent != MessageIntent.SOCIAL else None,
                confidence=0.99,
            )
        if len(mentioned_roles) == 2:
            return AddressingResult(
                addressing_type=AddressingType.MULTIPLE_AGENTS,
                target_agents=mentioned_roles,
                intent=intent,
                allow_multi_response=intent == MessageIntent.SOCIAL,
                requires_coordinator=intent != MessageIntent.SOCIAL,
                coordinator=(
                    AddressingDetector._work_coordinator(mentioned_roles)
                    if intent != MessageIntent.SOCIAL
                    else None
                ),
                confidence=0.99,
            )
        return AddressingResult(
            addressing_type=AddressingType.SINGLE_AGENT,
            target_agents=mentioned_roles,
            intent=intent,
            allow_multi_response=False,
            requires_coordinator=False,
            coordinator=mentioned_roles[0],
            confidence=0.99,
        )

    @classmethod
    async def detect(cls, message: NormalizedMessage) -> AddressingResult:
        text_lower = message.text.strip().lower()
        intent = intent_detector.detect_intent(message.text)

        # Explicit agent addressing always wins. The word "semua" may quantify an object,
        # but it must not erase an explicit "Manager dan Advisor" address.
        mentioned_roles = await cls._explicit_roles(text_lower)
        if mentioned_roles:
            return cls._result_for_explicit(mentioned_roles, intent)

        is_collective_vocative = any(
            re.search(pattern, text_lower) for pattern in cls.COLLECTIVE_VOCATIVE_PATTERNS
        )
        is_object_quantifier = any(
            re.search(pattern, text_lower) for pattern in cls.OBJECT_QUANTIFIER_PATTERNS
        )

        if is_collective_vocative:
            is_social = intent == MessageIntent.SOCIAL
            return AddressingResult(
                addressing_type=AddressingType.ALL_AGENTS,
                target_agents=[RoleID.MANAGER, RoleID.MARKETING, RoleID.ADVISOR],
                intent=intent,
                allow_multi_response=is_social,
                requires_coordinator=not is_social,
                coordinator=RoleID.MANAGER if not is_social else None,
                confidence=0.98,
            )

        if is_object_quantifier:
            return AddressingResult(
                addressing_type=AddressingType.NONE,
                target_agents=[],
                intent=intent,
                allow_multi_response=False,
                requires_coordinator=False,
                confidence=0.99,
            )

        return AddressingResult(
            addressing_type=AddressingType.NONE,
            target_agents=[],
            intent=intent,
            allow_multi_response=False,
            requires_coordinator=False,
            confidence=0.95,
        )


addressing_detector = AddressingDetector()
