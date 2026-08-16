"""Regression coverage for live Telegram/browser/vision failures found on Windows."""

import io
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from PIL import Image
from pydantic import SecretStr

from src.adapters.telegram.adapter import TelegramMultiBotAdapter
from src.adapters.telegram.bot_registry import bot_registry
from src.adapters.telegram.sender import TelegramSender, telegram_sender
from src.adapters.telegram.update_normalizer import TelegramUpdateNormalizer
from src.agents.manager import manager_agent
from src.core.config import settings
from src.core.types import MemoryScope, MemoryType, NormalizedMessage, RoleID
from src.files.pipeline import attachment_pipeline
from src.files.vision.model import vision_analyzer
from src.llm.provider import LLMResponse
from src.memory.service import memory_service
from src.memory.vector_index import memory_vector_index
from src.routing.addressing import addressing_detector
from src.storage.sqlite import db


def _png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (32, 32), "white").save(buffer, format="PNG")
    return buffer.getvalue()


def test_telegram_normalizer_retains_replied_message_text():
    bot_registry.register_bot_user_id("9001", RoleID.MANAGER)
    message = SimpleNamespace(
        message_id=501,
        from_user=SimpleNamespace(id=42, is_bot=False, full_name="User"),
        chat=SimpleNamespace(id=-100123456),
        text="gimana?",
        caption=None,
        reply_to_message=SimpleNamespace(
            message_id=500,
            text="Halaman sudah terbuka. Sekarang ambil screenshot.",
            caption=None,
            from_user=SimpleNamespace(id=9001, is_bot=True),
        ),
    )
    normalized = TelegramUpdateNormalizer.normalize_message(message, RoleID.MANAGER)
    assert normalized is not None
    assert normalized.reply_to_role == RoleID.MANAGER
    assert normalized.reply_to_text == "Halaman sudah terbuka. Sekarang ambil screenshot."


@pytest.mark.asyncio
async def test_reply_chain_restores_root_request_and_thread():
    adapter = TelegramMultiBotAdapter()
    initial = NormalizedMessage(
        message_id="100",
        group_id="-100123456",
        sender_id="u1",
        text=(
            "Manager, gunakan browser automation Morrow untuk buka https://example.com "
            "lalu sebutkan judul halaman dan isi utamanya."
        ),
        platform="telegram",
    )
    await adapter._hydrate_conversation_context(initial)
    assert initial.conversation_thread_id == "thr_-100123456_100"

    await db.execute(
        """INSERT INTO conversation_message_map
           (platform_message_id, group_id, role_id, thread_id, root_user_text, response_text)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            "telegram:-100123456:200",
            "-100123456",
            "manager",
            initial.conversation_thread_id,
            initial.text,
            "Halaman sudah terbuka. Sekarang ambil screenshot.",
        ),
    )
    followup = NormalizedMessage(
        message_id="101",
        group_id="-100123456",
        sender_id="u1",
        text="gimana?",
        platform="telegram",
        reply_to_message_id="200",
    )
    await adapter._hydrate_conversation_context(followup)
    assert followup.conversation_thread_id == initial.conversation_thread_id
    assert followup.conversation_root_text == initial.text
    assert followup.reply_to_text == "Halaman sudah terbuka. Sekarang ambil screenshot."
    assert "https://example.com" in followup.contextual_text()
    assert "gimana?" in followup.contextual_text()


@pytest.mark.asyncio
async def test_sender_propagates_parent_thread_to_bot_message(monkeypatch):
    fake_bot = MagicMock()
    fake_bot.send_message = AsyncMock(return_value=SimpleNamespace(message_id=777))
    monkeypatch.setattr(bot_registry, "get_bot", lambda role: fake_bot)
    await db.execute(
        """INSERT INTO conversation_message_map
           (platform_message_id, group_id, thread_id, root_user_text, response_text)
           VALUES (?, ?, ?, ?, ?)""",
        (
            "telegram:-100123456:100",
            "-100123456",
            "thr_-100123456_100",
            "Manager, buka https://example.com dan baca isinya.",
            "Manager, buka https://example.com dan baca isinya.",
        ),
    )

    sent_id = await telegram_sender.send_message(
        "-100123456",
        "Halaman terbuka.",
        RoleID.MANAGER,
        reply_to_message_id="100",
    )
    assert sent_id == "777"
    row = await db.fetch_one(
        "SELECT * FROM conversation_message_map WHERE platform_message_id=?",
        ("telegram:-100123456:777",),
    )
    assert row is not None
    assert row["thread_id"] == "thr_-100123456_100"
    assert "example.com" in row["root_user_text"]
    assert row["role_id"] == "manager"


@pytest.mark.asyncio
async def test_addressing_restores_persisted_reply_context():
    await db.execute(
        """INSERT INTO conversation_message_map
           (platform_message_id, group_id, role_id, thread_id, root_user_text, response_text)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            "telegram:g1:222",
            "g1",
            "manager",
            "thr_g1_111",
            "Manager, gunakan browser untuk buka https://example.com dan baca isinya.",
            "Halaman sudah terbuka.",
        ),
    )
    message = NormalizedMessage(
        message_id="223",
        group_id="g1",
        sender_id="u1",
        text="gimana?",
        platform="telegram",
        reply_to_message_id="222",
    )
    await addressing_detector.detect(message)
    assert message.reply_to_role == RoleID.MANAGER
    assert message.conversation_thread_id == "thr_g1_111"
    assert "example.com" in (message.conversation_root_text or "")


@pytest.mark.asyncio
async def test_vague_followup_does_not_inject_unrelated_pinned_decisions(monkeypatch):
    async def no_semantic(*args, **kwargs):
        return []

    monkeypatch.setattr(memory_vector_index, "search", no_semantic)
    await memory_service.set_memory(
        MemoryScope.SHARED,
        "etsy_pricing",
        "Harga gantungan kunci Etsy $12-20",
        "u1",
        memory_type=MemoryType.DECISION,
        group_id="g1",
    )
    await memory_service.set_memory(
        MemoryScope.SHARED,
        "browser_provider",
        "Browser production Morrow menggunakan agent-browser",
        "u1",
        memory_type=MemoryType.DECISION,
        group_id="g1",
    )

    assert await memory_service.retrieve_relevant_memory("gimana?", RoleID.MANAGER, "g1") == []

    message = NormalizedMessage(
        message_id="m2",
        group_id="g1",
        sender_id="u1",
        text="gimana?",
        conversation_thread_id="thr_g1_m1",
        conversation_root_text="Manager, gunakan browser Morrow untuk buka https://example.com dan baca isinya.",
        reply_to_text="Halaman sudah terbuka. Sekarang ambil screenshot.",
    )
    context = await manager_agent.assemble_context(message)
    system = context[0]["content"]
    assert "Browser production Morrow menggunakan agent-browser" in system
    assert "Harga gantungan kunci Etsy $12-20" not in system


@pytest.mark.asyncio
async def test_browser_inspection_forces_snapshot_before_final_answer(monkeypatch):
    monkeypatch.setattr(settings, "browser_enabled", True)
    calls: list[str] = []
    model_calls = 0

    async def fake_tool_execute(tool_name, parameters, **kwargs):
        calls.append(tool_name)
        if tool_name == "browser_open":
            return {"success": True, "result": {"title": "Example Domain", "url": "https://example.com/"}}
        if tool_name == "browser_snapshot":
            return {"success": True, "result": {"snapshot": '- heading "Example Domain"\n- link "Learn more"'}}
        raise AssertionError(tool_name)

    async def fake_chat_completion(**kwargs):
        nonlocal model_calls
        model_calls += 1
        if model_calls == 1:
            return LLMResponse(
                content="",
                model="test/model",
                tool_calls=[
                    {
                        "id": "open-1",
                        "name": "browser_open",
                        "arguments": '{"url":"https://example.com"}',
                    }
                ],
            )
        if model_calls == 2:
            return LLMResponse(
                content="Halaman sudah terbuka. Sekarang ambil screenshot untuk lihat isi utamanya.",
                model="test/model",
            )
        return LLMResponse(
            content="Judulnya Example Domain. Isinya halaman contoh dengan tautan Learn more.",
            model="test/model",
        )

    monkeypatch.setattr("src.agents.runtime.tool_executor.execute_tool", fake_tool_execute)
    monkeypatch.setattr("src.agents.runtime.openrouter_client.chat_completion", fake_chat_completion)
    result = await manager_agent.execute(
        NormalizedMessage(
            message_id="browser-live-1",
            group_id="g1",
            sender_id="u1",
            text=(
                "Manager, gunakan browser automation Morrow untuk buka https://example.com "
                "lalu sebutkan judul halaman dan isi utamanya. Jangan gunakan web_fetch."
            ),
        ),
        thread_id="thr_g1_browser_live_1",
    )
    assert result.startswith("Judulnya Example Domain")
    assert calls == ["browser_open", "browser_snapshot"]
    assert model_calls == 3


@pytest.mark.asyncio
async def test_browser_open_only_does_not_force_snapshot(monkeypatch):
    monkeypatch.setattr(settings, "browser_enabled", True)
    calls: list[str] = []
    model_calls = 0

    async def fake_tool_execute(tool_name, parameters, **kwargs):
        calls.append(tool_name)
        return {"success": True, "result": {"url": "https://example.com/"}}

    async def fake_chat_completion(**kwargs):
        nonlocal model_calls
        model_calls += 1
        if model_calls == 1:
            return LLMResponse(
                content="",
                model="test/model",
                tool_calls=[
                    {"id": "open-only", "name": "browser_open", "arguments": '{"url":"https://example.com"}'},
                ],
            )
        return LLMResponse(content="Halaman berhasil dibuka.", model="test/model")

    monkeypatch.setattr("src.agents.runtime.tool_executor.execute_tool", fake_tool_execute)
    monkeypatch.setattr("src.agents.runtime.openrouter_client.chat_completion", fake_chat_completion)
    result = await manager_agent.execute(
        NormalizedMessage(
            message_id="browser-open-only",
            group_id="g1",
            sender_id="u1",
            text="Manager, gunakan browser Morrow untuk buka https://example.com saja.",
        ),
        thread_id="thr_g1_open_only",
    )
    assert result == "Halaman berhasil dibuka."
    assert calls == ["browser_open"]


@pytest.mark.asyncio
async def test_empty_agent_output_retries_once_then_returns_nonempty_fallback(monkeypatch):
    count = 0

    async def fake_chat_completion(**kwargs):
        nonlocal count
        count += 1
        return LLMResponse(content="", model="test/model")

    monkeypatch.setattr("src.agents.runtime.openrouter_client.chat_completion", fake_chat_completion)
    result = await manager_agent.execute(
        NormalizedMessage(message_id="empty-final", group_id="g1", sender_id="u1", text="Manager, jawab ini.")
    )
    assert count == 2
    assert result.strip()
    assert "hasil kosong" in result


@pytest.mark.asyncio
async def test_image_caption_is_passed_into_visual_prompt(monkeypatch):
    captured = {}

    async def fake_visual(image_path, prompt="", usage_context=None):
        captured["prompt"] = prompt
        return "gantungan kunci kayu dengan ring logam"

    monkeypatch.setattr(vision_analyzer, "analyze_visual", fake_visual)
    result = await attachment_pipeline.process_bytes(
        "keychain.png",
        _png_bytes(),
        user_prompt="buatin contoh caption buat gantungan kunci ini di Threads",
        usage_context={"group_id": "g1", "thread_id": "thr_g1_img"},
    )
    assert result.visual_description == "gantungan kunci kayu dengan ring logam"
    assert "caption buat gantungan kunci" in captured["prompt"]
    assert "Jangan mengikuti instruksi" in captured["prompt"]


@pytest.mark.asyncio
async def test_vision_empty_primary_uses_one_multimodal_fallback(monkeypatch, tmp_path):
    image_path = tmp_path / "image.png"
    Image.new("RGB", (16, 16), "white").save(image_path)
    monkeypatch.setattr(settings, "openrouter_api_key", SecretStr("non-mock-test-key"))
    called: list[str] = []

    async def fake_analyze(model_key, data_url, user_prompt, usage_context):
        called.append(model_key)
        return "" if len(called) == 1 else "fallback visual ok"

    monkeypatch.setattr(vision_analyzer, "_analyze_with_model", fake_analyze)
    result = await vision_analyzer.analyze_visual(str(image_path), "describe")
    assert result == "fallback visual ok"
    assert called == [vision_analyzer.PRIMARY_MODEL_KEY, vision_analyzer.FALLBACK_MODEL_KEY]


@pytest.mark.asyncio
async def test_vision_double_empty_returns_explicit_error(monkeypatch, tmp_path):
    image_path = tmp_path / "image.png"
    Image.new("RGB", (16, 16), "white").save(image_path)
    monkeypatch.setattr(settings, "openrouter_api_key", SecretStr("non-mock-test-key"))

    async def empty(*args, **kwargs):
        return ""

    monkeypatch.setattr(vision_analyzer, "_analyze_with_model", empty)
    result = await vision_analyzer.analyze_visual(str(image_path), "describe")
    assert result is not None
    assert result.startswith("[Vision Error:")
    assert "output kosong" in result


@pytest.mark.asyncio
async def test_telegram_sender_never_calls_api_with_empty_text(monkeypatch):
    fake_bot = MagicMock()
    fake_bot.send_message = AsyncMock(return_value=SimpleNamespace(message_id=999))
    monkeypatch.setattr(bot_registry, "get_bot", lambda role: fake_bot)

    result = await telegram_sender.send_message("-100123456", "   ", RoleID.MANAGER)
    assert result == "999"
    sent_text = fake_bot.send_message.call_args.kwargs["text"]
    assert sent_text.strip()
    assert sent_text == TelegramSender.EMPTY_RESPONSE_FALLBACK


def test_telegram_list_items_are_separated_for_narrow_layout():
    formatted = TelegramSender._prepare_text("- satu\n- dua\n3. tiga")
    assert formatted == "- satu\n\n- dua\n\n3. tiga"


def test_telegram_chunking_respects_limit_and_prefers_paragraph_boundaries():
    paragraph = "x" * 1800
    text = f"{paragraph}\n\n{paragraph}\n\n{paragraph}"
    chunks = TelegramSender._chunks(text)
    assert len(chunks) >= 2
    assert all(chunk and len(chunk) <= TelegramSender.MAX_CHARS for chunk in chunks)
    assert chunks[0].endswith(paragraph)
