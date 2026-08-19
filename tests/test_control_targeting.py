"""Targeted stop/pause/resume must mutate only the requested durable task."""

import pytest

from src.core.types import RoleID, TaskStatus
from src.routing.intent import intent_detector
from src.tasks.service import task_service


@pytest.mark.asyncio
async def test_targeted_cancel_does_not_cancel_other_active_task():
    first = await task_service.create_task("g1", "first", initial_owner=RoleID.MANAGER)
    second = await task_service.create_task("g1", "second", initial_owner=RoleID.MARKETING)
    assert await task_service.update_task_status(first.id, TaskStatus.IN_PROGRESS)
    assert await task_service.update_task_status(second.id, TaskStatus.IN_PROGRESS)

    assert intent_detector.detect_control_command(f"batalkan task {first.id}") == "cancel"
    assert await task_service.cancel_active_tasks("g1") == 1

    first_after = await task_service.get_task(first.id)
    second_after = await task_service.get_task(second.id)
    assert first_after is not None and first_after.status == TaskStatus.CANCELLED
    assert second_after is not None and second_after.status == TaskStatus.IN_PROGRESS


@pytest.mark.asyncio
async def test_targeted_pause_and_resume_do_not_touch_other_task():
    first = await task_service.create_task("g1", "first", initial_owner=RoleID.MANAGER)
    second = await task_service.create_task("g1", "second", initial_owner=RoleID.MARKETING)
    assert await task_service.update_task_status(first.id, TaskStatus.IN_PROGRESS)
    assert await task_service.update_task_status(second.id, TaskStatus.IN_PROGRESS)

    assert intent_detector.detect_control_command(f"pause {first.id}") == "pause"
    assert await task_service.pause_active_tasks("g1") == 1
    assert (await task_service.get_task(first.id)).status == TaskStatus.WAITING_USER
    assert (await task_service.get_task(second.id)).status == TaskStatus.IN_PROGRESS

    assert intent_detector.detect_control_command(f"resume task {first.id}") == "resume"
    assert await task_service.resume_waiting_tasks("g1") == 1
    assert (await task_service.get_task(first.id)).status == TaskStatus.TODO
    assert (await task_service.get_task(second.id)).status == TaskStatus.IN_PROGRESS
