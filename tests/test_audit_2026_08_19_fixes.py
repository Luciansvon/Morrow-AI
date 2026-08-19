"""Regression coverage for verified findings from the 2026-08-19 audit."""

from __future__ import annotations

import httpx
import pytest

from src.core.config import settings
from src.integrations.immich import ImmichClient, ImmichDisabledError
from src.integrations.openviking import OpenVikingClient, OpenVikingDisabledError
from src.storage.sqlite import db
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
