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
        r"^@(semua|semuanya|tim|team)\b",
        (
            r"^(halo|hai|hey|hei|pagi|siang|sore|malam|selamat\s+\w+)\s+"
            r"(semua|semuanya|tim|team|guys|teman-teman|kalian)\b"
        ),
        (
            r"\b(apa\s+kabar|gimana\s+kabarnya)\s+"
            r"(semua|semuanya|tim|team|guys|teman-teman|kalian)\b"
        ),
        (
            r"\b(makasih|terima\s*kasih|thanks|thx)\s+"
            r"(semua|semuanya|tim|team|guys|teman-teman|kalian)\b"
        ),
        (
            r"^(kalian|kalian\s+semua|semua\s+orang)\s+"
            r"(gimana|ada|siap|lagi\s+apa|dengerin|tolong|bantu|kasih|beri)\b"
        ),
        r"^(semua|semuanya|tim|team)\s*,\s*",
        r"\b(semua\s+siap|semua\s+ada|tim\s+siap|tim\s+standby)\b",
        r"^(semua|semuanya)\s+(siap|ada|dengerin|tolong\s+dengar)\b",
        (
            r"^(semua|semuanya|tim|team|kalian)\s+"
            r"(tolong|bantu|kasih|beri|coba|cek|analisis|audit|nilai|evaluasi|riset|cari|buat|susun)\b"
        ),
        (
            r"\b(kalian|semua|semuanya)\s+(kasih|beri)\s+"
            r"(pendapat|masukan|opini|pandangan|saran)\b"
        ),
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

    DIRECT_PREFIXES: ClassVar[tuple[str, ...]] = (
        "halo",
        "hai",
        "hey",
        "hei",
        "pagi",
        "siang",
        "sore",
        "malam",
        "tolong",
        "minta",
        "panggil",
    )
    DIRECT_FOLLOW_ACTIONS: ClassVar[tuple[str, ...]] = (
        "tolong",
        "bantu",
        "cek",
        "buat",
        "nilai",
        "evaluasi",
        "analisis",
        "audit",
        "riset",
        "cari",
        "jelaskan",
        "jawab",
        "kasih",
        "beri",
        "susun",
    )

    @staticmethod
    async def _role_aliases() -> list[tuple[str, RoleID]]:
        rows = await db.fetch_all("SELECT role_id, display_name FROM agents")
        display_names = {row["role_id"]: row["display_name"] for row in rows}
        aliases: list[tuple[str, RoleID]] = []
        seen: set[tuple[str, RoleID]] = set()
        for role in (RoleID.MANAGER, RoleID.MARKETING, RoleID.ADVISOR):
            terms = [role.value]
            display_name = str(display_names.get(role.value, "")).strip().lower()
            if display_name:
                terms.append(display_name)
            username = bot_registry.get_username(role)
            if username:
                terms.append(username.lower())
            for term in terms:
                key = (term, role)
                if term and key not in seen:
                    aliases.append(key)
                    seen.add(key)
        return aliases

    @classmethod
    async def _explicit_roles(cls, text_lower: str) -> list[RoleID]:
        """Return only actual direct addresses, preserving the user's mention order.

        @mentions are explicit anywhere. Bare role/display names are considered addresses only
        in the leading vocative/imperative clause, so phrases such as
        "apa bedanya manager dan advisor" stay ordinary questions instead of fan-out requests.
        """
        aliases = await cls._role_aliases()
        positions: dict[RoleID, int] = {}

        for alias, role in aliases:
            pattern = rf"(?<!\w)@{re.escape(alias)}(?!\w)"
            for match in re.finditer(pattern, text_lower):
                positions[role] = min(positions.get(role, match.start()), match.start())

        alias_terms = sorted({alias for alias, _ in aliases}, key=len, reverse=True)
        if alias_terms:
            alias_re = "(?:" + "|".join(re.escape(alias) for alias in alias_terms) + ")"
            prefix_re = "(?:" + "|".join(re.escape(x) for x in cls.DIRECT_PREFIXES) + ")"
            action_re = "(?:" + "|".join(re.escape(x) for x in cls.DIRECT_FOLLOW_ACTIONS) + ")"
            direct = re.match(
                rf"^\s*(?:(?:{prefix_re})\s+)?"
                rf"(?P<head>{alias_re}(?:\s*(?:dan|&|,)\s*{alias_re}){{0,2}})"
                rf"(?=\s*(?:[,;:]|\b{action_re}\b|$))",
                text_lower,
            )
            if direct:
                head_start = direct.start("head")
                head = direct.group("head")
                for alias, role in aliases:
                    match = re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", head)
                    if match:
                        absolute = head_start + match.start()
                        positions[role] = min(positions.get(role, absolute), absolute)

        return [role for role, _ in sorted(positions.items(), key=lambda item: item[1])]

    @staticmethod
    async def _restore_reply_context(message: NormalizedMessage) -> None:
        """Enrich a Telegram reply with the original thread/root request before routing."""
        if not message.reply_to_message_id:
            return
        canonical = f"{message.platform}:{message.group_id}:{message.reply_to_message_id}"
        row = await db.fetch_one(
            """SELECT role_id, thread_id, task_id, root_user_text, response_text
               FROM conversation_message_map WHERE platform_message_id=? AND group_id=?""",
            (canonical, message.group_id),
        )
        if row:
            if message.reply_to_role is None and row.get("role_id"):
                message.reply_to_role = RoleID(row["role_id"])
            message.conversation_thread_id = row.get("thread_id") or message.conversation_thread_id
            message.conversation_task_id = row.get("task_id") or message.conversation_task_id
            message.conversation_root_text = row.get("root_user_text") or message.conversation_root_text
            if not message.reply_to_text:
                message.reply_to_text = row.get("response_text") or None
            return

        legacy = await db.fetch_one(
            "SELECT originating_role_id FROM message_agent_map WHERE platform_message_id=?",
            (canonical,),
        )
        if not legacy:
            legacy = await db.fetch_one(
                """SELECT originating_role_id FROM message_agent_map
                   WHERE platform_message_id=? AND group_id=?""",
                (message.reply_to_message_id, message.group_id),
            )
        if message.reply_to_role is None and legacy and legacy.get("originating_role_id"):
            message.reply_to_role = RoleID(legacy["originating_role_id"])

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
        await cls._restore_reply_context(message)
        text_lower = message.text.strip().lower()
        intent = intent_detector.detect_intent(message.text)

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
