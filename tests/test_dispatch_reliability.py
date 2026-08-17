"""Regression coverage for audit-driven dispatch and execution reliability fixes."""

import asyncio

import pytest

from src.adapters.cli import CLIAdapter
from src.core.normalizer import MessageNormalizer
from src.core.orchestrator import SystemOrchestrator
from src.core.types import AddressingType, MessageIntent, NormalizedMessage, RoleID, TaskStatus
from src.routing.addressing import addressing_detector
from src.routing.intent import intent_detector
from src.storage.sqlite import db
from src.tasks.service import task_service


@pytest.mark.asyncio
@pytest.mark.parametrize("text", ["terimakasih semua", "terima kasih semua", "makasih semua"])
async def test_thanks_all_is_social_broadcast_to_all_agents(text):
    msg = NormalizedMessage(message_id=f"thanks-{abs(hash(text))}", group_id="g1", sender_id="u1", text=text)
    result = await addressing_detector.detect(msg)
    assert result.intent == MessageIntent.SOCIAL
    assert result.addressing_type == AddressingType.ALL_AGENTS
    assert result.target_agents == [RoleID.MANAGER, RoleID.MARKETING, RoleID.ADVISOR]


@pytest.mark.asyncio
async def test_semua_tolong_without_comma_is_collective_work_request():
    msg = NormalizedMessage(
        message_id="collective-no-comma",
        group_id="g1",
        sender_id="u1",
        text="semua tolong analisis ini",
    )
    result = await addressing_detector.detect(msg)
    assert result.intent == MessageIntent.WORK_REQUEST
    assert result.addressing_type == AddressingType.ALL_AGENTS
    assert result.requires_coordinator is True
    assert result.coordinator == RoleID.MANAGER


@pytest.mark.asyncio
async def test_role_names_as_question_objects_do_not_fan_out():
    msg = NormalizedMessage(
        message_id="role-object-question",
        group_id="g1",
        sender_id="u1",
        text="apa bedanya manager dan advisor di perusahaan?",
    )
    result = await addressing_detector.detect(msg)
    assert result.intent == MessageIntent.QUESTION
    assert result.addressing_type == AddressingType.NONE
    assert result.target_agents == []


@pytest.mark.asyncio
async def test_explicit_role_order_is_preserved_when_manager_not_present():
    msg = NormalizedMessage(
        message_id="ordered-addressing",
        group_id="g1",
        sender_id="u1",
        text="Advisor dan Marketing, nilai rencana ini",
    )
    result = await addressing_detector.detect(msg)
    assert result.target_agents == [RoleID.ADVISOR, RoleID.MARKETING]
    assert result.coordinator == RoleID.ADVISOR


def test_cancel_words_are_commands_even_when_social_word_is_present():
    assert intent_detector.detect_intent("makasih, batal aja semua task") == MessageIntent.COMMAND
    assert intent_detector.detect_control_command("makasih, batal aja semua task") == "cancel"
    assert intent_detector.detect_control_command("jangan lanjutkan") == "cancel"


@pytest.mark.asyncio
async def test_collective_work_attempts_all_targets_and_records_partial_failure(monkeypatch):
    adapter = CLIAdapter()
    orchestrator = SystemOrchestrator(adapter)
    calls: list[RoleID] = []

    async def fake_execute(message, role, **kwargs):
        calls.append(role)
        if role == RoleID.MARKETING:
            raise RuntimeError("marketing unavailable")
        return f"hasil-{role.value}"

    monkeypatch.setattr(orchestrator, "_execute_agent", fake_execute)
    result = await orchestrator.handle_incoming_message(
        NormalizedMessage(
            message_id="collective-partial-failure",
            group_id="g1",
            sender_id="u1",
            text="semua tolong analisis strategi ini",
        )
    )

    assert calls == [RoleID.MANAGER, RoleID.MARKETING, RoleID.ADVISOR]
    assert result is not None and "marketing" in result.lower() and "belum lengkap" in result.lower()

    active = await task_service.list_active_tasks("g1")
    task = next(task for task in active if task.title.startswith("semua tolong analisis"))
    assert task.status == TaskStatus.BLOCKED
    runs = {row["role_id"]: row for row in await task_service.list_agent_runs(task.id)}
    assert runs["manager"]["status"] == "succeeded"
    assert runs["marketing"]["status"] == "failed"
    assert runs["advisor"]["status"] == "succeeded"


@pytest.mark.asyncio
async def test_collective_work_requires_three_of_three_before_done(monkeypatch):
    adapter = CLIAdapter()
    orchestrator = SystemOrchestrator(adapter)
    calls: list[RoleID] = []

    async def fake_execute(message, role, **kwargs):
        calls.append(role)
        return f"hasil-{role.value}"

    monkeypatch.setattr(orchestrator, "_execute_agent", fake_execute)
    result = await orchestrator.handle_incoming_message(
        NormalizedMessage(
            message_id="collective-all-success",
            group_id="g1",
            sender_id="u1",
            text="semua tolong audit rencana launch ini",
        )
    )
    assert result is not None
    assert calls[:3] == [RoleID.MANAGER, RoleID.MARKETING, RoleID.ADVISOR]
    assert calls[-1] == RoleID.MANAGER  # synthesis only after all three contributions

    history = await task_service.list_task_history("g1")
    task = next(task for task in history if task.title.startswith("semua tolong audit"))
    assert task.status == TaskStatus.DONE
    runs = await task_service.list_agent_runs(task.id)
    assert {row["role_id"] for row in runs} == {"manager", "marketing", "advisor"}
    assert all(row["status"] == "succeeded" for row in runs)


@pytest.mark.asyncio
async def test_failed_event_can_be_reclaimed_but_completed_event_cannot():
    event_id = "event-lifecycle-reclaim"
    assert await MessageNormalizer.claim_event(event_id, "telegram", "g1") is True
    assert await MessageNormalizer.claim_event(event_id, "telegram", "g1") is False

    await MessageNormalizer.mark_event_failed(event_id, "telegram", "g1", "boom")
    assert await MessageNormalizer.claim_event(event_id, "telegram", "g1") is True

    await MessageNormalizer.mark_event_completed(event_id, "telegram", "g1")
    assert await MessageNormalizer.claim_event(event_id, "telegram", "g1") is False
    row = await db.fetch_one(
        "SELECT status, attempt_count FROM processed_events WHERE event_id=?",
        (MessageNormalizer.canonical_event_id(event_id, "telegram", "g1"),),
    )
    assert row is not None
    assert row["status"] == "completed"
    assert row["attempt_count"] == 2


@pytest.mark.asyncio
async def test_cancel_bypasses_group_lock_and_suppresses_stale_answer(monkeypatch):
    adapter = CLIAdapter()
    orchestrator = SystemOrchestrator(adapter)
    started = asyncio.Event()
    release = asyncio.Event()

    async def slow_execute(message, role, **kwargs):
        started.set()
        await release.wait()
        return "jawaban lama yang tidak boleh terkirim"

    monkeypatch.setattr(orchestrator, "_execute_agent", slow_execute)
    work = asyncio.create_task(
        orchestrator.handle_incoming_message(
            NormalizedMessage(
                message_id="slow-work",
                group_id="g1",
                sender_id="u1",
                text="Manager, analisis ini",
            )
        )
    )
    await asyncio.wait_for(started.wait(), timeout=1)

    cancel_result = await asyncio.wait_for(
        orchestrator.handle_incoming_message(
            NormalizedMessage(
                message_id="urgent-cancel",
                group_id="g1",
                sender_id="u1",
                text="stop",
            )
        ),
        timeout=1,
    )
    assert cancel_result is not None and "Dihentikan" in cancel_result

    release.set()
    stale_result = await asyncio.wait_for(work, timeout=1)
    assert stale_result == "Permintaan dihentikan oleh pengguna."
    assert not any("jawaban lama" in item["text"] for item in adapter.sent_messages)


@pytest.mark.asyncio
async def test_new_collaboration_binds_task_and_thread_to_conversation(monkeypatch):
    adapter = CLIAdapter()
    orchestrator = SystemOrchestrator(adapter)
    canonical = "telegram:g1:continuity-work"
    await db.execute(
        """INSERT INTO conversation_message_map
           (platform_message_id, group_id, role_id, thread_id, task_id, root_user_text, response_text)
           VALUES (?, ?, NULL, ?, NULL, ?, ?)""",
        (canonical, "g1", "thr_g1_continuity-work", "semua tolong cek ini", "semua tolong cek ini"),
    )

    async def fake_execute(message, role, **kwargs):
        return f"hasil-{role.value}"

    monkeypatch.setattr(orchestrator, "_execute_agent", fake_execute)
    await orchestrator.handle_incoming_message(
        NormalizedMessage(
            message_id="continuity-work",
            group_id="g1",
            sender_id="u1",
            text="semua tolong cek ini",
            event_claimed=True,
        )
    )
    row = await db.fetch_one(
        "SELECT task_id, thread_id FROM conversation_message_map WHERE platform_message_id=?",
        (canonical,),
    )
    assert row is not None
    assert row["task_id"] and row["task_id"].startswith("task_")
    assert row["thread_id"] == "thr_g1_continuity-work"
