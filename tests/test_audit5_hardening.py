"""Regression tests added by the five-pass reliability audit."""

import asyncio
import io
import time
import zipfile
from types import SimpleNamespace

import pytest
from PIL import Image
from pydantic import SecretStr

from src.adapters.base import BaseChannelAdapter
from src.adapters.telegram.bot_registry import bot_registry
from src.adapters.telegram.sender import telegram_sender
from src.adapters.telegram.update_normalizer import TelegramUpdateNormalizer
from src.approval.gateway import approval_gateway
from src.core.config import settings
from src.core.orchestrator import SystemOrchestrator
from src.core.types import (
    AddressingType,
    AttachmentInfo,
    MemoryScope,
    NormalizedMessage,
    RoleID,
    TaskStatus,
)
from src.files.intake import file_intake
from src.files.vision.model import vision_analyzer
from src.memory.service import memory_service
from src.routing.addressing import addressing_detector
from src.routing.fast_path import fast_path_router
from src.storage.attachments import attachment_storage
from src.storage.sqlite import DatabaseManager, db
from src.tasks.handoff import task_handoff
from src.tasks.service import task_service
from src.tools.executor import tool_executor
from src.tools.registry import tool_registry


class CaptureAdapter(BaseChannelAdapter):
    def __init__(self):
        super().__init__()
        self.sent: list[tuple[RoleID | None, str]] = []

    async def start(self):
        return None

    async def stop(self):
        return None

    async def send_message(
        self,
        group_id,
        text,
        from_role=None,
        reply_to_message_id=None,
    ):
        self.sent.append((from_role, text))
        return str(len(self.sent))

    async def send_approval_prompt(self, group_id, approval_id, action_description, parameters):
        return None


@pytest.mark.asyncio
async def test_explicit_roles_win_over_object_quantifier():
    result = await addressing_detector.detect(
        NormalizedMessage(
            message_id="addr-explicit",
            group_id="g1",
            sender_id="u1",
            text="Manager dan Advisor, hitung semua harga ini",
        )
    )
    assert result.addressing_type == AddressingType.MULTIPLE_AGENTS
    assert result.target_agents == [RoleID.MANAGER, RoleID.ADVISOR]


@pytest.mark.asyncio
async def test_registered_bot_usernames_are_valid_multi_agent_addresses(monkeypatch):
    monkeypatch.setattr(
        bot_registry,
        "_bot_usernames",
        {
            RoleID.MANAGER: "morrow_manager_bot",
            RoleID.MARKETING: "morrow_marketing_bot",
        },
    )
    result = await addressing_detector.detect(
        NormalizedMessage(
            message_id="addr-usernames",
            group_id="g1",
            sender_id="u1",
            text="@morrow_manager_bot dan @morrow_marketing_bot, halo",
        )
    )
    assert result.addressing_type == AddressingType.MULTIPLE_AGENTS
    assert result.target_agents == [RoleID.MANAGER, RoleID.MARKETING]




@pytest.mark.asyncio
async def test_custom_display_names_work_for_multi_agent_addressing():
    await db.execute("UPDATE agents SET display_name='Ari' WHERE role_id='manager'")
    await db.execute("UPDATE agents SET display_name='Naya' WHERE role_id='marketing'")
    result = await addressing_detector.detect(
        NormalizedMessage(
            message_id="addr-display-names",
            group_id="g1",
            sender_id="u1",
            text="Ari dan Naya, halo",
        )
    )
    assert result.addressing_type == AddressingType.MULTIPLE_AGENTS
    assert result.target_agents == [RoleID.MANAGER, RoleID.MARKETING]




@pytest.mark.asyncio
async def test_reply_to_bot_identity_routes_without_message_map(monkeypatch):
    bot_registry.register_bot_user_id("9001", RoleID.MARKETING)
    message = SimpleNamespace(
        message_id=501,
        from_user=SimpleNamespace(id=42, is_bot=False, full_name="User"),
        chat=SimpleNamespace(id=-100777),
        text="kenapa?",
        caption=None,
        reply_to_message=SimpleNamespace(
            message_id=123,
            from_user=SimpleNamespace(id=9001, is_bot=True),
        ),
    )
    normalized = TelegramUpdateNormalizer.normalize_message(message, RoleID.MANAGER)
    assert normalized is not None
    assert normalized.reply_to_role == RoleID.MARKETING
    routed = await fast_path_router.resolve_fast_path(normalized)
    assert routed is not None
    assert routed[0] == RoleID.MARKETING

@pytest.mark.asyncio
async def test_telegram_sender_never_fabricates_message_id(monkeypatch):
    monkeypatch.setattr(bot_registry, "_bots", {})
    with pytest.raises(RuntimeError, match="belum siap"):
        await telegram_sender.send_message("-100123456", "hello", RoleID.MANAGER)


@pytest.mark.asyncio
async def test_rejected_spoofed_file_is_not_left_on_disk():
    result = await file_intake.process_incoming_file("invoice.pdf", b"MZ-not-a-pdf")
    assert result.is_supported is False
    assert result.file_path == ""


@pytest.mark.asyncio
async def test_attachment_storage_resolves_settings_lazily(monkeypatch, tmp_path):
    new_root = tmp_path / "new-storage"
    monkeypatch.setattr(settings, "storage_dir", str(new_root))
    file_id, path, _ = attachment_storage.save_file("note.txt", b"hello")
    try:
        assert str(new_root.resolve()) in path
    finally:
        attachment_storage.remove_file(file_id)


@pytest.mark.asyncio
async def test_ooxml_archive_expansion_limit(monkeypatch):
    monkeypatch.setattr(settings, "max_archive_uncompressed_mb", 1)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("xl/workbook.xml", "<workbook/>")
        archive.writestr("xl/worksheets/sheet1.xml", "0" * (2 * 1024 * 1024))
    result = await file_intake.process_incoming_file("large.xlsx", buffer.getvalue())
    assert result.is_supported is False
    assert "melebihi batas" in (result.error_message or "")
    assert result.file_path == ""


@pytest.mark.asyncio
async def test_vision_usage_is_attributed_to_group(monkeypatch, tmp_path):
    image_path = tmp_path / "image.png"
    Image.new("RGB", (16, 16), "white").save(image_path)
    captured = {}

    async def fake_completion(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(content="visual ok")

    monkeypatch.setattr(settings, "openrouter_api_key", SecretStr("non-mock-test-key"))
    from src.files.vision import model as vision_module

    monkeypatch.setattr(vision_module.openrouter_client, "chat_completion", fake_completion)
    result = await vision_analyzer.analyze_visual(
        str(image_path),
        usage_context={"group_id": "g1", "thread_id": "thr_g1_m1"},
    )
    assert result == "visual ok"
    assert captured["usage_context"]["group_id"] == "g1"
    assert captured["usage_context"]["thread_id"] == "thr_g1_m1"




@pytest.mark.asyncio
async def test_db_ordinary_write_waits_for_explicit_transaction():
    transaction_open = asyncio.Event()
    release_transaction = asyncio.Event()
    outside_finished = asyncio.Event()

    async def hold_transaction():
        async with db.transaction() as conn:
            await conn.execute(
                "INSERT INTO processed_events (event_id, platform, group_id) VALUES (?, ?, ?)",
                ("txn-held", "test", "g1"),
            )
            transaction_open.set()
            await release_transaction.wait()

    async def outside_write():
        await transaction_open.wait()
        await db.execute(
            "INSERT INTO processed_events (event_id, platform, group_id) VALUES (?, ?, ?)",
            ("outside-write", "test", "g1"),
        )
        outside_finished.set()

    holder = asyncio.create_task(hold_transaction())
    writer = asyncio.create_task(outside_write())
    await transaction_open.wait()
    await asyncio.sleep(0.02)
    assert outside_finished.is_set() is False
    release_transaction.set()
    await asyncio.gather(holder, writer)
    assert outside_finished.is_set() is True


@pytest.mark.asyncio
async def test_concurrent_memory_updates_keep_single_memory_row():
    await asyncio.gather(
        memory_service.set_memory(
            scope=MemoryScope.SHARED,
            key="concurrent-key",
            value="A",
            changed_by_actor="u1",
            group_id="g1",
        ),
        memory_service.set_memory(
            scope=MemoryScope.SHARED,
            key="concurrent-key",
            value="B",
            changed_by_actor="u2",
            group_id="g1",
        ),
    )
    rows = await db.fetch_all(
        "SELECT * FROM memories WHERE group_id=? AND scope='shared' AND key=?",
        ("g1", "concurrent-key"),
    )
    audit = await memory_service.get_memory_audit_history("concurrent-key", "g1")
    assert len(rows) == 1
    assert len(audit) == 2


@pytest.mark.asyncio
async def test_concurrent_handoffs_have_single_winner():
    task = await task_service.create_task("g1", "handoff-race", initial_owner=RoleID.MANAGER)
    outcomes = await asyncio.gather(
        task_handoff.handoff_task(
            task.id,
            RoleID.MANAGER,
            RoleID.MARKETING,
            "marketing",
        ),
        task_handoff.handoff_task(
            task.id,
            RoleID.MANAGER,
            RoleID.ADVISOR,
            "advisor",
        ),
    )
    assert sum(ok for ok, _ in outcomes) == 1
    current = await task_service.get_task(task.id)
    assert current is not None
    assert current.current_owner in {RoleID.MARKETING, RoleID.ADVISOR}


@pytest.mark.asyncio
async def test_only_one_concurrent_approval_wins():
    request = await approval_gateway.create_request(
        "g1",
        "send_email",
        {"to": "client@example.com"},
        RoleID.MANAGER,
    )
    outcomes = await asyncio.gather(
        approval_gateway.approve_request(request.approval_id, "u1", expected_group_id="g1"),
        approval_gateway.approve_request(request.approval_id, "u1", expected_group_id="g1"),
    )
    assert sum(ok for ok, _ in outcomes) == 1


@pytest.mark.asyncio
async def test_concurrent_approval_execution_runs_side_effect_once():
    calls = 0

    async def fake_send_email(to: str):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.02)
        return {"to": to}

    tool_registry.register_tool("send_email", fake_send_email)
    request = await approval_gateway.create_request(
        "g1",
        "send_email",
        {"to": "client@example.com"},
        RoleID.MANAGER,
    )
    ok, _ = await approval_gateway.approve_request(
        request.approval_id,
        "u1",
        expected_group_id="g1",
    )
    assert ok is True
    results = await asyncio.gather(
        approval_gateway.execute_approved_request(request.approval_id),
        approval_gateway.execute_approved_request(request.approval_id),
    )
    assert calls == 1
    assert sum(bool(item.get("success")) for item in results) == 1


@pytest.mark.asyncio
async def test_idempotency_key_is_bound_to_tool_and_parameters():
    async def fake_send_email(to: str):
        return {"to": to}

    tool_registry.register_tool("send_email", fake_send_email)
    first = await tool_executor.execute_tool(
        "send_email",
        {"to": "a@example.com"},
        idempotency_key="same-key",
        is_approved=True,
    )
    second = await tool_executor.execute_tool(
        "send_email",
        {"to": "b@example.com"},
        idempotency_key="same-key",
        is_approved=True,
    )
    assert first["success"] is True
    assert second["success"] is False
    assert second["error"] == "IDEMPOTENCY_KEY_CONFLICT"


@pytest.mark.asyncio
async def test_unknown_tool_policy_fails_closed():
    result = await tool_executor.execute_tool(
        "new_dangerous_tool",
        {"target": "external"},
        is_approved=True,
    )
    assert result["success"] is False
    assert result["error"] == "TOOL_POLICY_UNCLASSIFIED"


@pytest.mark.asyncio
async def test_known_internal_missing_tool_reports_not_registered():
    result = await tool_executor.execute_tool("read_attachment", {"file_id": "x"})
    assert result["success"] is False
    assert result["error"] == "TOOL_NOT_REGISTERED"




@pytest.mark.asyncio
async def test_single_agent_social_greeting_is_zero_token(monkeypatch):
    adapter = CaptureAdapter()
    orchestrator = SystemOrchestrator(adapter)

    async def explode(*args, **kwargs):
        raise AssertionError("LLM tidak boleh dipanggil untuk greeting sosial deterministik")

    for agent in orchestrator._agents.values():
        monkeypatch.setattr(agent, "execute", explode)
    result = await orchestrator.handle_incoming_message(
        NormalizedMessage(
            message_id="single-social-zero",
            group_id="group_core_team_01",
            sender_id="user_bima_01",
            text="Manager, halo",
        )
    )
    assert result is not None
    assert len(adapter.sent) == 1
    assert adapter.sent[0][0] == RoleID.MANAGER


@pytest.mark.asyncio
async def test_unaddressed_social_greeting_defaults_to_manager_without_llm(monkeypatch):
    adapter = CaptureAdapter()
    orchestrator = SystemOrchestrator(adapter)

    async def explode(*args, **kwargs):
        raise AssertionError("LLM tidak boleh dipanggil untuk greeting sosial deterministik")

    for agent in orchestrator._agents.values():
        monkeypatch.setattr(agent, "execute", explode)
    result = await orchestrator.handle_incoming_message(
        NormalizedMessage(
            message_id="generic-social-zero",
            group_id="group_core_team_01",
            sender_id="user_bima_01",
            text="halo",
        )
    )
    assert result is not None
    assert len(adapter.sent) == 1
    assert adapter.sent[0][0] == RoleID.MANAGER


@pytest.mark.asyncio
async def test_incomplete_collective_work_is_waiting_user(monkeypatch):
    adapter = CaptureAdapter()
    orchestrator = SystemOrchestrator(adapter)

    async def fake_execute(*args, **kwargs):
        return "kontribusi"

    for agent in orchestrator._agents.values():
        monkeypatch.setattr(agent, "execute", fake_execute)

    checks = iter([True, False])

    async def fake_budget(*args, **kwargs):
        return next(checks, False)

    from src.core import orchestrator as orchestrator_module

    monkeypatch.setattr(orchestrator_module.usage_meter, "check_thread_budget", fake_budget)
    message = NormalizedMessage(
        message_id="incomplete-collab",
        group_id="group_core_team_01",
        sender_id="user_bima_01",
        text="semua, bantu strategi launch",
        event_claimed=True,
    )
    result = await orchestrator._run_collective_work(
        message,
        [RoleID.MANAGER, RoleID.MARKETING, RoleID.ADVISOR],
        RoleID.MANAGER,
    )
    assert "dijeda" in result
    active = await task_service.list_active_tasks("group_core_team_01")
    matching = [task for task in active if task.title == "semua, bantu strategi launch"]
    assert matching
    assert matching[0].status == TaskStatus.WAITING_USER


@pytest.mark.asyncio
async def test_task_history_contains_terminal_tasks_only():
    done = await task_service.create_task("g1", "done-task")
    active = await task_service.create_task("g1", "active-task")
    await task_service.update_task_status(done.id, TaskStatus.DONE)
    await task_service.update_task_status(active.id, TaskStatus.IN_PROGRESS)
    history = await task_service.list_task_history("g1")
    assert done.id in {task.id for task in history}
    assert active.id not in {task.id for task in history}


@pytest.mark.asyncio
async def test_task_retry_budget_must_be_positive():
    with pytest.raises(ValueError, match="max_retries"):
        await task_service.create_task("g1", "bad-retry", max_retries=0)


@pytest.mark.asyncio
async def test_rejected_file_is_not_persisted_as_attachment():
    result = await file_intake.process_incoming_file("payload.pdf", b"MZ-not-pdf")
    row = await db.fetch_one("SELECT file_id FROM attachments WHERE file_id=?", (result.file_id,))
    assert result.is_supported is False
    assert row is None


@pytest.mark.asyncio
async def test_sync_spreadsheet_parser_is_offloaded_from_event_loop(monkeypatch, tmp_path):
    from src.files import pipeline as pipeline_module
    from src.files.pipeline import attachment_pipeline

    csv_path = tmp_path / "slow.csv"
    csv_path.write_text("a,b\n1,2\n", encoding="utf-8")

    async def fake_intake(filename, content):
        return AttachmentInfo(
            file_id="slow-file",
            original_name="slow.csv",
            detected_mime="text/csv",
            file_path=str(csv_path),
            file_size=csv_path.stat().st_size,
            is_supported=True,
        )

    def slow_parse(path):
        time.sleep(0.08)
        return "parsed", {"default": [["1", "2"]]}

    monkeypatch.setattr(pipeline_module.file_intake, "process_incoming_file", fake_intake)
    monkeypatch.setattr(pipeline_module.spreadsheet_parser, "parse_csv", slow_parse)

    task = asyncio.create_task(attachment_pipeline.process_bytes("slow.csv", b"x"))
    await asyncio.sleep(0.02)
    assert task.done() is False
    result = await task
    assert result.extracted_text == "parsed"


@pytest.mark.asyncio
async def test_memory_migration_deduplicates_before_unique_indexes(tmp_path):
    path = tmp_path / "legacy.db"
    manager = DatabaseManager(str(path))
    conn = await manager.connect()
    await conn.execute(
        """CREATE TABLE memories (
            id TEXT PRIMARY KEY, group_id TEXT NOT NULL, scope TEXT NOT NULL, role_id TEXT,
            key TEXT NOT NULL, value TEXT NOT NULL, memory_type TEXT NOT NULL DEFAULT 'fact',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )"""
    )
    await conn.execute(
        "INSERT INTO memories (id, group_id, scope, role_id, key, value) VALUES ('old1','g','shared',NULL,'k','A')"
    )
    await conn.execute(
        "INSERT INTO memories (id, group_id, scope, role_id, key, value) VALUES ('old2','g','shared',NULL,'k','B')"
    )
    await conn.commit()
    try:
        await manager.init_schema()
        rows = await manager.fetch_all(
            "SELECT value FROM memories WHERE group_id='g' AND scope='shared' AND key='k'"
        )
        assert len(rows) == 1
        assert rows[0]["value"] in {"A", "B"}
    finally:
        await manager.close()
