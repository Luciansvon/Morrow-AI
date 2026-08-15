"""Regression coverage for Morrow v0.2.5 Reliable Action Layer."""

import sqlite3

import pytest

from src.agents.manager import manager_agent
from src.approval.gateway import approval_gateway
from src.browser.agent_browser import AgentBrowserBackend
from src.browser.base import BrowserActionClass
from src.core.config import settings
from src.core.types import NormalizedMessage, RoleID
from src.llm.provider import LLMResponse
from src.storage.sqlite import DatabaseManager, db
from src.tools.builtins import ensure_builtin_tools_registered
from src.tools.executor import tool_executor
from src.tools.policy import tool_policy
from src.tools.registry import ToolCapability, tool_registry


def _function_names(tools):
    return {item.get("function", {}).get("name") for item in tools or [] if item.get("type") == "function"}


@pytest.mark.asyncio
async def test_progressive_discovery_loads_schema_only_after_search(monkeypatch):
    calls = {"count": 0}
    async def fake_chat_completion(*, messages, tools=None, **kwargs):
        calls["count"] += 1
        names = _function_names(tools)
        if calls["count"] == 1:
            assert "morrow_tool_search" in names
            assert "calculate" not in names
            return LLMResponse(content="", model="test/model", tool_calls=[{"id": "discover-1", "name": "morrow_tool_search", "arguments": '{"query":"calculator arithmetic hitung"}'}])
        if calls["count"] == 2:
            assert "calculate" in names
            return LLMResponse(content="", model="test/model", tool_calls=[{"id": "calc-1", "name": "calculate", "arguments": '{"expression":"7*6"}'}])
        assert any(item.get("role") == "tool" and '"result": 42' in item.get("content", "") for item in messages)
        return LLMResponse(content="42", model="test/model")
    monkeypatch.setattr("src.agents.runtime.openrouter_client.chat_completion", fake_chat_completion)
    result = await manager_agent.execute(NormalizedMessage(message_id="discovery-1", group_id="group_core_team_01", sender_id="user_bima_01", text="Manager, bantu gue pakai tool yang tepat"))
    assert result == "42"
    assert calls["count"] == 3


@pytest.mark.asyncio
async def test_internal_tool_execution_is_journaled_with_provenance():
    ensure_builtin_tools_registered()
    result = await tool_executor.execute_tool("calculate", {"expression": "6*7"}, execution_context={"group_id": "g1", "thread_id": "thr-1", "task_id": "task-1", "role_id": "manager"})
    assert result["success"] is True
    assert result["result"]["result"] == 42
    assert result["provenance"]["trust_class"] == "trusted_internal"
    row = await db.fetch_one("SELECT * FROM tool_executions WHERE execution_id=?", (result["execution_id"],))
    assert row is not None
    assert row["group_id"] == "g1"
    assert row["thread_id"] == "thr-1"
    assert row["task_id"] == "task-1"
    assert row["role_id"] == "manager"
    assert row["classification"] == "internal"
    assert row["capability"] == "read"
    assert row["policy_decision"] == "allow"
    assert row["status"] == "succeeded"
    assert row["side_effect"] == 0
    assert row["provenance_json"]


@pytest.mark.asyncio
async def test_unknown_tool_denial_is_journaled():
    result = await tool_executor.execute_tool("definitely_not_allowed", {"x": 1}, execution_context={"group_id": "g1", "role_id": "manager"})
    assert result["success"] is False
    assert result["error"] == "TOOL_POLICY_UNCLASSIFIED"
    row = await db.fetch_one("SELECT * FROM tool_executions WHERE execution_id=?", (result["execution_id"],))
    assert row is not None
    assert row["status"] == "denied"
    assert row["policy_decision"] == "deny_unclassified"


@pytest.mark.asyncio
async def test_external_tool_call_creates_scoped_approval_without_execution(monkeypatch):
    calls = {"side_effect": 0, "llm": 0}
    async def fake_send_email(to: str, subject: str):
        calls["side_effect"] += 1
        return {"to": to, "subject": subject}
    tool_registry.register_tool("send_email", fake_send_email, description="Kirim email eksternal.", parameters={"type": "object", "properties": {"to": {"type": "string"}, "subject": {"type": "string"}}, "required": ["to", "subject"], "additionalProperties": False}, domain="email", capability=ToolCapability.COMMIT, risk="high", side_effect=True, output_trust="external", retry_safe=False, keywords={"email", "kirim", "send"})
    async def fake_chat_completion(*, messages, tools=None, **kwargs):
        calls["llm"] += 1
        if calls["llm"] == 1:
            assert "send_email" in _function_names(tools)
            return LLMResponse(content="", model="test/model", tool_calls=[{"id": "mail-1", "name": "send_email", "arguments": '{"to":"client@example.com","subject":"Halo"}'}])
        tool_messages = [item for item in messages if item.get("role") == "tool"]
        assert tool_messages
        assert '"requires_approval": true' in tool_messages[-1]["content"]
        assert "appr_" in tool_messages[-1]["content"]
        return LLMResponse(content="Email sudah disiapkan dan menunggu approval.", model="test/model")
    monkeypatch.setattr("src.agents.runtime.openrouter_client.chat_completion", fake_chat_completion)
    result = await manager_agent.execute(NormalizedMessage(message_id="approval-runtime-1", group_id="group_core_team_01", sender_id="user_bima_01", text="Manager, kirim email ke client@example.com dengan subject Halo"))
    assert "menunggu approval" in result
    assert calls["side_effect"] == 0
    approvals = await db.fetch_all("SELECT * FROM approvals WHERE group_id=? AND action_type='send_email'", ("group_core_team_01",))
    assert len(approvals) == 1
    assert approvals[0]["status"] == "pending"
    journal = await db.fetch_all("SELECT * FROM tool_executions WHERE approval_id=?", (approvals[0]["approval_id"],))
    assert len(journal) == 1
    assert journal[0]["status"] == "approval_required"
    assert journal[0]["policy_decision"] == "approval_required"


@pytest.mark.asyncio
async def test_approved_external_execution_links_approval_to_journal():
    calls = {"count": 0}
    async def fake_send_email(to: str):
        calls["count"] += 1
        return {"to": to}
    tool_registry.register_tool("send_email", fake_send_email, domain="email", capability=ToolCapability.COMMIT, risk="high", side_effect=True, output_trust="external", retry_safe=False, keywords={"email"})
    request = await approval_gateway.create_request("g1", "send_email", {"to": "client@example.com"}, RoleID.MANAGER)
    ok, _ = await approval_gateway.approve_request(request.approval_id, "u1", expected_group_id="g1")
    assert ok is True
    result = await approval_gateway.execute_approved_request(request.approval_id)
    assert result["success"] is True
    assert calls["count"] == 1
    assert result["tool_execution_id"]
    row = await db.fetch_one("SELECT * FROM tool_executions WHERE execution_id=?", (result["tool_execution_id"],))
    assert row is not None
    assert row["approval_id"] == request.approval_id
    assert row["classification"] == "external"
    assert row["side_effect"] == 1
    assert row["retry_safe"] == 0


@pytest.mark.asyncio
async def test_legacy_external_registration_cannot_downgrade_commit_metadata():
    async def fake_send_email(to: str):
        return {"to": to}
    tool_registry.register_tool("send_email", fake_send_email)
    request = await approval_gateway.create_request("g1", "send_email", {"to": "client@example.com"}, RoleID.MANAGER)
    ok, _ = await approval_gateway.approve_request(request.approval_id, "u1", expected_group_id="g1")
    assert ok is True
    result = await approval_gateway.execute_approved_request(request.approval_id)
    assert result["success"] is True
    row = await db.fetch_one("SELECT * FROM tool_executions WHERE execution_id=?", (result["tool_execution_id"],))
    assert row is not None
    assert row["classification"] == "external"
    assert row["capability"] == "commit"
    assert row["side_effect"] == 1
    assert row["retry_safe"] == 0


@pytest.mark.asyncio
async def test_browser_click_cannot_be_downgraded_to_prepare():
    backend = AgentBrowserBackend(executable="not-used")
    with pytest.raises(ValueError, match="minimal diklasifikasikan sebagai commit"):
        await backend.interact("click", {"target": "@e1"}, task_space="task-1", action_class=BrowserActionClass.PREPARE)


def test_browser_task_space_is_sanitized_and_stable():
    first = AgentBrowserBackend._session_name("task:abc / unsafe")
    second = AgentBrowserBackend._session_name("task:abc / unsafe")
    assert first == second
    assert ":" not in first
    assert "/" not in first
    assert len(first) <= 64


def test_browser_tools_are_feature_gated(monkeypatch):
    monkeypatch.setattr(settings, "browser_enabled", True)
    ensure_builtin_tools_registered()
    click = tool_registry.get_registered_tool("browser_click")
    assert click is not None
    assert click.capability == ToolCapability.COMMIT
    assert click.side_effect is True
    assert click.retry_safe is False
    assert tool_policy.classify("browser_click") == "external"


@pytest.mark.asyncio
async def test_v024_tool_execution_table_migrates_to_journal(tmp_path):
    path = tmp_path / "legacy.db"
    conn = sqlite3.connect(path)
    conn.execute("""CREATE TABLE tool_executions (idempotency_key TEXT PRIMARY KEY, tool_name TEXT NOT NULL, parameters_json TEXT NOT NULL, status TEXT NOT NULL, result_json TEXT, error_text TEXT, started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, finished_at TIMESTAMP)""")
    conn.execute("""INSERT INTO tool_executions (idempotency_key, tool_name, parameters_json, status, result_json) VALUES ('idem-old', 'send_email', '{"to":"x@example.com"}', 'succeeded', '{"ok":true}')""")
    conn.commit()
    conn.close()
    manager = DatabaseManager(str(path))
    try:
        await manager.init_schema()
        columns = await manager._table_columns("tool_executions")
        assert "execution_id" in columns
        assert "policy_decision" in columns
        row = await manager.fetch_one("SELECT * FROM tool_executions WHERE idempotency_key='idem-old'")
        assert row is not None
        assert row["execution_id"].startswith("legacy_")
        assert row["policy_decision"] == "legacy_import"
    finally:
        await manager.close()
