"""Regression coverage for verified findings from the 2026-08-19 audit."""

from __future__ import annotations

import httpx
import pytest

from src.core.config import settings
from src.core.types import RoleID, TaskStatus
from src.integrations.immich import ImmichClient, ImmichDisabledError
from src.integrations.openviking import OpenVikingClient, OpenVikingDisabledError
from src.storage.sqlite import db
from src.tasks.service import task_service
from src.tools.executor import tool_executor
from src.tools.registry import ToolCapability, tool_registry


@pytest.mark.asyncio
async def test_executor_enforces_registered_numeric_schema_before_call():
    calls = {"count": 0}

    async def bounded_tool(value: int):
        calls["count"] += 1
        return value

    tool_registry.register_tool(
        "calculate",
        bounded_tool,
        parameters={
            "type": "object",
            "properties": {"value": {"type": "integer", "minimum": 0, "maximum": 5}},
            "required": ["value"],
            "additionalProperties": False,
        },
        capability=ToolCapability.READ,
    )

    result = await tool_executor.execute_tool("calculate", {"value": 999})

    assert result["success"] is False
    assert result["error"] == "TOOL_PARAMETERS_INVALID"
    assert calls["count"] == 0
    row = await db.fetch_one(
        "SELECT policy_decision, status, error_text FROM tool_executions WHERE execution_id=?",
        (result["execution_id"],),
    )
    assert row is not None
    assert row["policy_decision"] == "deny_invalid_parameters"
    assert row["status"] == "denied"
    assert "maksimal 5" in row["error_text"]


@pytest.mark.asyncio
async def test_executor_rejects_extra_parameters_before_call():
    calls = {"count": 0}

    async def strict_tool(value: str):
        calls["count"] += 1
        return value

    tool_registry.register_tool(
        "calculate",
        strict_tool,
        parameters={
            "type": "object",
            "properties": {"value": {"type": "string", "minLength": 1}},
            "required": ["value"],
            "additionalProperties": False,
        },
    )

    result = await tool_executor.execute_tool("calculate", {"value": "ok", "surprise": True})
    assert result["success"] is False
    assert result["error"] == "TOOL_PARAMETERS_INVALID"
    assert calls["count"] == 0


@pytest.mark.asyncio
async def test_task_dependency_blocks_start_until_dependency_done():
    dependency = await task_service.create_task("g1", "dependency", initial_owner=RoleID.MANAGER)
    child = await task_service.create_task(
        "g1",
        "dependent",
        initial_owner=RoleID.MANAGER,
        dependencies=[dependency.id],
    )

    assert await task_service.update_task_status(child.id, TaskStatus.IN_PROGRESS) is False
    assert (await task_service.get_task(child.id)).status == TaskStatus.TODO

    assert await task_service.update_task_status(dependency.id, TaskStatus.IN_PROGRESS) is True
    assert await task_service.update_task_status(dependency.id, TaskStatus.DONE) is True
    assert await task_service.update_task_status(child.id, TaskStatus.IN_PROGRESS) is True


@pytest.mark.asyncio
async def test_terminal_task_cannot_be_reopened():
    task = await task_service.create_task("g1", "terminal", initial_owner=RoleID.MANAGER)
    assert await task_service.update_task_status(task.id, TaskStatus.IN_PROGRESS) is True
    assert await task_service.update_task_status(task.id, TaskStatus.DONE) is True
    assert await task_service.update_task_status(task.id, TaskStatus.IN_PROGRESS) is False
    assert (await task_service.get_task(task.id)).status == TaskStatus.DONE


@pytest.mark.asyncio
async def test_task_model_uses_persisted_timestamps():
    task = await task_service.create_task("g1", "timestamps", initial_owner=RoleID.MANAGER)
    await db.execute(
        """UPDATE tasks
           SET created_at='2025-01-02 03:04:05', updated_at='2025-02-03 04:05:06'
           WHERE id=?""",
        (task.id,),
    )
    loaded = await task_service.get_task(task.id)
    assert loaded is not None
    assert loaded.created_at.year == 2025 and loaded.created_at.month == 1 and loaded.created_at.day == 2
    assert loaded.updated_at.year == 2025 and loaded.updated_at.month == 2 and loaded.updated_at.day == 3


@pytest.mark.asyncio
async def test_pause_cancels_running_agent_ledger_and_stale_completion_is_rejected():
    task = await task_service.create_task("g1", "pause run", initial_owner=RoleID.MANAGER)
    assert await task_service.update_task_status(task.id, TaskStatus.IN_PROGRESS) is True
    await task_service.start_agent_run(task.id, RoleID.MANAGER)

    assert await task_service.pause_task(task.id) is True
    runs = await task_service.list_agent_runs(task.id)
    assert runs[0]["status"] == "cancelled"
    assert await task_service.complete_agent_run(task.id, RoleID.MANAGER, "stale") is False
    assert (await task_service.get_task(task.id)).status == TaskStatus.WAITING_USER


def test_integration_flags_default_to_off():
    assert settings.openviking_enabled is False
    assert settings.immich_enabled is False
    assert settings.morrow_v03_orchestrator_enabled is False


@pytest.mark.asyncio
async def test_openviking_fails_closed_when_disabled():
    client = OpenVikingClient(enabled=False, base_url="http://openviking.invalid", api_key="x")
    with pytest.raises(OpenVikingDisabledError):
        await client.find("project context")


@pytest.mark.asyncio
async def test_immich_fails_closed_when_disabled():
    client = ImmichClient(enabled=False, base_url="http://immich.invalid", api_key="x")
    with pytest.raises(ImmichDisabledError):
        await client.search_assets()


@pytest.mark.asyncio
async def test_openviking_find_uses_scoped_headers_and_expected_endpoint():
    seen: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["api_key"] = request.headers.get("X-API-Key")
        seen["account"] = request.headers.get("X-OpenViking-Account")
        seen["user"] = request.headers.get("X-OpenViking-User")
        return httpx.Response(200, json={"status": "ok", "result": {"items": []}})

    client = OpenVikingClient(
        enabled=True,
        base_url="http://openviking.test",
        api_key="secret-test-key",
        account="workspace-1",
        user="user-1",
        transport=httpx.MockTransport(handler),
    )
    result = await client.find("morrow")

    assert result == {"items": []}
    assert seen == {
        "path": "/api/v1/search/find",
        "api_key": "secret-test-key",
        "account": "workspace-1",
        "user": "user-1",
    }


@pytest.mark.asyncio
async def test_immich_search_rejects_client_controlled_owner_scope():
    client = ImmichClient(
        enabled=True,
        base_url="http://immich.test",
        api_key="secret-test-key",
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={})),
    )
    with pytest.raises(ValueError, match="Ownership scope"):
        await client.search_assets(filters={"userIds": ["someone-else"]})
