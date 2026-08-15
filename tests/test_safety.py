"""Pengujian Kontrak Penerimaan AC-011, AC-014, AC-015: Safety & Anti-Loop Guard."""

import pytest

from src.core.types import RoleID, TaskModel, TaskStatus
from src.safety.conflict_detector import conflict_detector
from src.safety.loop_guard import loop_guard


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


@pytest.mark.asyncio
async def test_ac014_max_4_turns_loop_guard():
    """AC-014: Diskusi otomatis antar agen berhenti setelah tepat 4 putaran."""
    thread_id = "thread_loop_test_99"
    group_id = "group_core_team_01"

    # Putaran 1 s.d. 4 harus diizinkan
    for turn in range(1, 5):
        can_cont, msg, cur_turn = await loop_guard.can_continue_discussion(
            thread_id=thread_id,
            group_id=group_id,
            proposing_role=RoleID.MANAGER if turn % 2 == 1 else RoleID.MARKETING,
        )
        assert can_cont is True
        assert cur_turn == turn

    # Putaran ke-5 harus DITOLAK
    can_cont, msg, cur_turn = await loop_guard.can_continue_discussion(
        thread_id=thread_id,
        group_id=group_id,
        proposing_role=RoleID.ADVISOR,
    )
    assert can_cont is False
    assert "waiting_user" in msg
