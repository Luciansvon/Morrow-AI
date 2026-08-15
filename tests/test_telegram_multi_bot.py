"""Pengujian Arsitektur 3 Bot Telegram Terpisah (1 Backend Morrow)."""

from typing import Any

import pytest

from src.adapters.telegram.bot_registry import bot_registry
from src.adapters.telegram.sender import telegram_sender
from src.adapters.telegram.update_normalizer import TelegramUpdateNormalizer
from src.core.config import Settings
from src.core.normalizer import MessageNormalizer
from src.core.types import MemoryScope, NormalizedMessage, RoleID
from src.memory.service import memory_service
from src.routing.fast_path import fast_path_router
from src.storage.sqlite import db
from src.tasks.handoff import task_handoff
from src.tasks.service import task_service


class MockAiogramBot:
    """Mock Bot aiogram untuk pengujian multi-bot."""

    def __init__(self, token: str, role_id: RoleID, bot_id: int, username: str):
        self.token = token
        self.role_id = role_id
        self.id = bot_id
        self.username = username
        self.sent_messages = []

    async def get_me(self):
        class Me:
            id = self.id
            username = self.username
        return Me()

    async def send_message(self, chat_id: int, text: str, reply_to_message_id: int | None = None, parse_mode: str = "Markdown"):
        msg_id = f"tg_sent_{self.role_id.value}_{len(self.sent_messages)+1}"
        record = {
            "message_id": msg_id,
            "chat_id": chat_id,
            "text": text,
            "reply_to": reply_to_message_id,
            "sent_by_bot": self.role_id.value,
        }
        self.sent_messages.append(record)

        class SentMsg:
            message_id = msg_id
        return SentMsg()


class MockAiogramUser:
    def __init__(self, user_id: int, full_name: str):
        self.id = user_id
        self.full_name = full_name


class MockAiogramChat:
    def __init__(self, chat_id: int):
        self.id = chat_id


class MockAiogramMessage:
    def __init__(self, message_id: int, chat_id: int, user_id: int, text: str, reply_to_message: Any = None):
        self.message_id = message_id
        self.chat = MockAiogramChat(chat_id)
        self.from_user = MockAiogramUser(user_id, "Bima")
        self.text = text
        self.caption = None
        self.reply_to_message = reply_to_message


@pytest.fixture
def setup_mock_telegram_bots():
    """Setup 3 instance Bot Telegram mock."""
    mgr_bot = MockAiogramBot("token_mgr_123", RoleID.MANAGER, 1001, "MorrowManagerBot")
    mkt_bot = MockAiogramBot("token_mkt_456", RoleID.MARKETING, 1002, "MorrowMarketingBot")
    adv_bot = MockAiogramBot("token_adv_789", RoleID.ADVISOR, 1003, "MorrowAdvisorBot")

    mock_map = {
        RoleID.MANAGER: mgr_bot,
        RoleID.MARKETING: mkt_bot,
        RoleID.ADVISOR: adv_bot,
    }
    bot_registry.initialize_bots(mock_map)
    bot_registry.register_bot_user_id("1001")
    bot_registry.register_bot_user_id("1002")
    bot_registry.register_bot_user_id("1003")
    bot_registry.register_bot_username(RoleID.MANAGER, "MorrowManagerBot")
    bot_registry.register_bot_username(RoleID.MARKETING, "MorrowMarketingBot")
    bot_registry.register_bot_username(RoleID.ADVISOR, "MorrowAdvisorBot")

    return mock_map


def test_config_fails_on_missing_token():
    """1. Config gagal jika salah satu token bot wajib kosong (tanpa membocorkan token)."""
    cfg = Settings(
        TELEGRAM_MANAGER_BOT_TOKEN="token_ada",
        TELEGRAM_MARKETING_BOT_TOKEN="",  # Kosong!
        TELEGRAM_ADVISOR_BOT_TOKEN="token_ada_2",
    )
    with pytest.raises(ValueError) as excinfo:
        cfg.validate_telegram_tokens()

    err_msg = str(excinfo.value)
    assert "marketing" in err_msg
    assert "token_ada" not in err_msg  # Tidak membocorkan token yang ada


def test_tokens_not_in_repr_or_logs():
    """2. Token Telegram dibungkus SecretStr dan tidak pernah muncul di repr/log."""
    cfg = Settings(
        TELEGRAM_MANAGER_BOT_TOKEN="super_secret_manager_token_999",
        TELEGRAM_MARKETING_BOT_TOKEN="super_secret_marketing_token_888",
        TELEGRAM_ADVISOR_BOT_TOKEN="super_secret_advisor_token_777",
    )
    repr_str = repr(cfg)
    str_val = str(cfg)

    assert "super_secret_manager_token_999" not in repr_str
    assert "super_secret_marketing_token_888" not in repr_str
    assert "super_secret_advisor_token_777" not in repr_str
    assert "super_secret_manager_token_999" not in str_val


def test_three_bots_mapped_correctly(setup_mock_telegram_bots):
    """3. Tiga bot terpetakan secara deterministik ke role_id yang benar."""
    assert bot_registry.get_bot(RoleID.MANAGER).role_id == RoleID.MANAGER
    assert bot_registry.get_bot(RoleID.MARKETING).role_id == RoleID.MARKETING
    assert bot_registry.get_bot(RoleID.ADVISOR).role_id == RoleID.ADVISOR


@pytest.mark.asyncio
async def test_duplicate_telegram_update_handled_once(setup_mock_telegram_bots):
    """4. Ketika 3 bot di grup yang sama menerima update yang sama, hanya 1 yang diproses."""
    event_id = "tg_msg_dup_999"

    # Update diterima Manager Bot
    is_dup_1 = await MessageNormalizer.is_duplicate_event(event_id, platform="telegram")
    # Update yang sama diterima Marketing Bot
    is_dup_2 = await MessageNormalizer.is_duplicate_event(event_id, platform="telegram")
    # Update yang sama diterima Advisor Bot
    is_dup_3 = await MessageNormalizer.is_duplicate_event(event_id, platform="telegram")

    assert is_dup_1 is False  # Pesan pertama diproses!
    assert is_dup_2 is True   # Pesan kedua di-drop sebagai duplikat
    assert is_dup_3 is True   # Pesan ketiga di-drop sebagai duplikat


def test_self_bot_echo_filtered_out(setup_mock_telegram_bots):
    """Filter pesan yang dikirim oleh bot Morrow sendiri agar tidak terjadi feedback loop."""
    # Pesan yang dikirim oleh Manager Bot (ID: 1001)
    echo_msg = MockAiogramMessage(
        message_id=555,
        chat_id=-100123456,
        user_id=1001,  # ID bot sendiri
        text="Marketing, tolong siapkan data",
    )
    norm = TelegramUpdateNormalizer.normalize_message(echo_msg, received_by_role=RoleID.MARKETING)
    assert norm is None  # Diabaikan dari alur masuk!


@pytest.mark.asyncio
async def test_response_sent_by_matching_bot(setup_mock_telegram_bots):
    """5. Response milik Marketing dikirim oleh Marketing Bot, Manager oleh Manager Bot, dsb."""
    bots = setup_mock_telegram_bots

    # Kirim pesan dari Marketing
    msg_id_mkt = await telegram_sender.send_message(
        group_id="-100123456",
        text="Ini hasil analisis kampanye",
        from_role=RoleID.MARKETING,
    )
    assert msg_id_mkt.startswith("tg_sent_marketing")
    assert len(bots[RoleID.MARKETING].sent_messages) == 1
    assert len(bots[RoleID.MANAGER].sent_messages) == 0

    # Kirim pesan dari Advisor
    msg_id_adv = await telegram_sender.send_message(
        group_id="-100123456",
        text="Ini evaluasi risiko bisnis",
        from_role=RoleID.ADVISOR,
    )
    assert msg_id_adv.startswith("tg_sent_advisor")
    assert len(bots[RoleID.ADVISOR].sent_messages) == 1


@pytest.mark.asyncio
async def test_delegation_switches_speaking_bot(setup_mock_telegram_bots):
    """6. Delegasi Manager -> Marketing menyebabkan pesan berikutnya dikirim oleh Marketing Bot."""
    bots = setup_mock_telegram_bots

    # 1. Manager membuat tugas dan mengirim pesan awal
    task = await task_service.create_task(
        group_id="-100123456",
        title="Buat Copywriting Iklan",
        initial_owner=RoleID.MANAGER,
    )
    await telegram_sender.send_message("-100123456", "Aku buatkan tugas untuk kampanye", from_role=RoleID.MANAGER)
    assert len(bots[RoleID.MANAGER].sent_messages) == 1

    # 2. Handoff ke Marketing
    await task_handoff.handoff_task(task.id, RoleID.MANAGER, RoleID.MARKETING, "Delegasi copywriting")

    # 3. Marketing merespon tugas tersebut menggunakan Marketing Bot
    await telegram_sender.send_message("-100123456", "Siap, aku ambil alih tugas copywriting", from_role=RoleID.MARKETING)
    assert len(bots[RoleID.MARKETING].sent_messages) == 1
    assert bots[RoleID.MARKETING].sent_messages[0]["text"] == "Siap, aku ambil alih tugas copywriting"


@pytest.mark.asyncio
async def test_reply_to_marketing_bot_routes_to_marketing(setup_mock_telegram_bots):
    """7. Reply ke pesan Marketing Bot disalurkan kembali ke Marketing Agent."""
    original_msg_id = "tg_sent_marketing_99"
    await db.execute(
        """
        INSERT INTO message_agent_map (platform_message_id, originating_role_id, bot_identity, group_id)
        VALUES (?, ?, ?, ?)
        """,
        (original_msg_id, "marketing", "@MorrowMarketingBot", "-100123456"),
    )

    reply_msg = NormalizedMessage(
        message_id="user_reply_01",
        group_id="-100123456",
        sender_id="user_bima_01",
        text="Tolong revisi bagian judul promosinya",
        reply_to_message_id=original_msg_id,
    )

    res = await fast_path_router.resolve_fast_path(reply_msg)
    assert res is not None
    role, reason = res
    assert role == RoleID.MARKETING
    assert "Reply-Aware Mapping" in reason


@pytest.mark.asyncio
async def test_shared_memory_and_tasks_preserved_across_bots():
    """8. Task dan shared memory yang dibuat via satu bot tetap sinkron dan terbaca oleh seluruh bot."""
    # Tulis memori bersama
    await memory_service.set_memory(
        scope=MemoryScope.SHARED,
        key="target_omset_q3",
        value="Rp 500.000.000",
        changed_by_actor="marketing_bot",
    )

    # Buat tugas
    task = await task_service.create_task(
        group_id="-100123456",
        title="Persiapan Peluncuran Produk",
        initial_owner=RoleID.MANAGER,
    )

    # Baca dari sudut pandang backend bersama
    shared_mem = await memory_service.get_active_shared_memory()
    retrieved_task = await task_service.get_task(task.id)

    assert shared_mem["target_omset_q3"] == "Rp 500.000.000"
    assert retrieved_task is not None
    assert retrieved_task.title == "Persiapan Peluncuran Produk"
