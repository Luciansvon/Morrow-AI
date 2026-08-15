"""Pengujian Kontrak Penerimaan AC-011, AC-014, AC-015: Safety & Anti-Loop Guard."""

import pytest

from src.core.types import NormalizedMessage, RoleID, TaskModel, TaskStatus
from src.safety.conflict_detector import conflict_detector
from src.safety.loop_guard import loop_guard
from src.tasks.service import task_service


def test_ac011_and_ac015_conflict_detection():
    """AC-011 & AC-015: Instruksi yang bertentangan dengan tugas aktif memicu jeda otomatis."""
    active_task = TaskModel(
        id="task_live_01",
        title="Luncurkan Iklan FB Ads",
        current_owner=RoleID.MARKETING,
        status=TaskStatus.IN_PROGRESS,
    )

    is_conflict, desc, task = conflict_detector.detect_conflict(
        new_instruction="Tolong batalkan rencana iklan sekarang",
        active_tasks=[active_task],
    )
    assert is_conflict is True
    assert task.id == "task_live_01"
    assert "berpotensi membatalkan/mengubah tugas aktif" in desc


def test_conflict_detector_targets_matching_task_when_multiple_are_active():
    campaign = TaskModel(
        id="task_campaign",
        title="Campaign Iklan Instagram",
        current_owner=RoleID.MARKETING,
        status=TaskStatus.IN_PROGRESS,
    )
    report = TaskModel(
        id="task_report",
        title="Laporan Penjualan Mingguan",
        current_owner=RoleID.MANAGER,
        status=TaskStatus.IN_PROGRESS,
    )

    is_conflict, _, task = conflict_detector.detect_conflict(
        new_instruction="Batalkan laporan penjualan mingguan",
        active_tasks=[campaign, report],
    )

    assert is_conflict is True
    assert task is not None
    assert task.id == "task_report"


def test_conflict_detector_does_not_pick_arbitrary_task_when_target_is_ambiguous():
    first = TaskModel(
        id="task_first",
        title="Campaign Iklan Instagram",
        current_owner=RoleID.MARKETING,
        status=TaskStatus.IN_PROGRESS,
    )
    second = TaskModel(
        id="task_second",
        title="Laporan Penjualan Mingguan",
        current_owner=RoleID.MANAGER,
        status=TaskStatus.IN_PROGRESS,
    )

    is_conflict, desc, task = conflict_detector.detect_conflict(
        new_instruction="Batalkan yang itu sekarang",
        active_tasks=[first, second],
    )

    assert is_conflict is True
    assert task is None
    assert "ambigu" in desc.lower()


@pytest.mark.asyncio
async def test_ambiguous_conflict_does_not_pause_arbitrary_task(orchestrator):
    first = await task_service.create_task(
        group_id="group_core_team_01",
        title="Campaign Iklan Instagram",
        initial_owner=RoleID.MARKETING,
    )
    second = await task_service.create_task(
        group_id="group_core_team_01",
        title="Laporan Penjualan Mingguan",
        initial_owner=RoleID.MANAGER,
    )
    await task_service.update_task_status(first.id, TaskStatus.IN_PROGRESS)
    await task_service.update_task_status(second.id, TaskStatus.IN_PROGRESS)

    result = await orchestrator.handle_incoming_message(
        NormalizedMessage(
            message_id="ambiguous_conflict_01",
            group_id="group_core_team_01",
            sender_id="user_bima_01",
            text="Batalkan yang itu sekarang",
            platform="cli",
        )
    )

    assert result is not None
    assert "ambigu" in result.lower()
    first_after = await task_service.get_task(first.id)
    second_after = await task_service.get_task(second.id)
    assert first_after is not None and first_after.status == TaskStatus.IN_PROGRESS
    assert second_after is not None and second_after.status == TaskStatus.IN_PROGRESS


@pytest.mark.asyncio
async def test_ac014_max_4_turns_loop_guard():
    """AC-014: Diskusi otomatis antar agen berhenti setelah tepat 4 putaran."""
    thread_id = "thread_loop_test_99"
    group_id = "group_core_team_01"

    for turn in range(1, 5):
        can_cont, msg, cur_turn = await loop_guard.can_continue_discussion(
            thread_id=thread_id,
            group_id=group_id,
            proposing_role=RoleID.MANAGER if turn % 2 == 1 else RoleID.MARKETING,
        )
        assert can_cont is True
        assert cur_turn == turn

    can_cont, msg, cur_turn = await loop_guard.can_continue_discussion(
        thread_id=thread_id,
        group_id=group_id,
        proposing_role=RoleID.ADVISOR,
    )
    assert can_cont is False
    assert "waiting_user" in msg
