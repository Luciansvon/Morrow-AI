"""Pengujian Kontrak Penerimaan AC-006: Internal Task Handoff & Anti-Cycle Guard."""

import pytest

from src.core.types import RoleID, TaskStatus
from src.tasks.handoff import task_handoff
from src.tasks.service import task_service


@pytest.mark.asyncio
async def test_ac006_internal_handoff_without_user_approval():
    """AC-006: Tugas internal dapat didelegasikan antar agen tanpa persetujuan manual pengguna."""
    task = await task_service.create_task(
        group_id="group_core_team_01",
        title="Riset Kompetitor Pasar",
        description="Analisis positioning produk kompetitor utama",
        initial_owner=RoleID.MANAGER,
    )
    assert task.current_owner == RoleID.MANAGER

    success, msg = await task_handoff.handoff_task(
        task_id=task.id,
        from_role=RoleID.MANAGER,
        to_role=RoleID.MARKETING,
        reason="Kebutuhan riset strategi pemasaran",
    )
    assert success is True

    updated_task = await task_service.get_task(task.id)
    assert updated_task.current_owner == RoleID.MARKETING


@pytest.mark.asyncio
async def test_ac006_anti_cycle_handoff_guard():
    """AC-006 Anti-Cycle: Dilarang mengembalikan tugas ke agen yang sudah pernah mencoba di rantai yang sama."""
    task = await task_service.create_task(
        group_id="group_core_team_01",
        title="Tugas Uji Siklus",
        initial_owner=RoleID.MANAGER,
    )

    await task_handoff.handoff_task(
        task_id=task.id,
        from_role=RoleID.MANAGER,
        to_role=RoleID.MARKETING,
        reason="Oper alih 1",
    )
    await task_handoff.handoff_task(
        task_id=task.id,
        from_role=RoleID.MARKETING,
        to_role=RoleID.ADVISOR,
        reason="Oper alih 2",
    )

    success, error_msg = await task_handoff.handoff_task(
        task_id=task.id,
        from_role=RoleID.ADVISOR,
        to_role=RoleID.MANAGER,
        reason="Oper alih terlarang (loop)",
    )
    assert success is False
    assert "Anti-Cycle Guard" in error_msg


@pytest.mark.asyncio
@pytest.mark.parametrize("terminal_status", [TaskStatus.DONE, TaskStatus.FAILED, TaskStatus.CANCELLED])
async def test_terminal_task_cannot_be_reopened_by_handoff(terminal_status):
    task = await task_service.create_task(
        group_id="group_core_team_01",
        title=f"Terminal task {terminal_status.value}",
        initial_owner=RoleID.MANAGER,
    )
    assert await task_service.update_task_status(task.id, terminal_status)

    success, message = await task_handoff.handoff_task(
        task_id=task.id,
        from_role=RoleID.MANAGER,
        to_role=RoleID.MARKETING,
        reason="should not reopen terminal task",
    )

    assert success is False
    assert "terminal" in message.lower()
    persisted = await task_service.get_task(task.id)
    assert persisted is not None
    assert persisted.status == terminal_status
    assert persisted.current_owner == RoleID.MANAGER
