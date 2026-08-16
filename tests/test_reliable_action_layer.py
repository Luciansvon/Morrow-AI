"""Regression coverage for Morrow v0.2.5 Reliable Action Layer."""

import json
import sqlite3

import pytest

from src.agents.manager import manager_agent
from src.approval.fingerprint import fingerprinter
from src.approval.gateway import approval_gateway
from src.browser.agent_browser import AgentBrowserBackend, BrowserBackendUnavailableError
from src.browser.base import BrowserActionClass
from src.core.config import settings
from src.core.types import NormalizedMessage, RoleID
from src.llm.provider import LLMResponse
from src.storage.sqlite import DatabaseManager, db
from src.tools.builtins import ensure_builtin_tools_registered
from src.tools.executor import UnknownExternalResultError, tool_executor
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
async def test_registered_but_undiscovered_tool_cannot_execute(monkeypatch):
    """P0: Tool terdaftar di registry tetapi belum diekspos tidak boleh dieksekusi saat ditebak model."""
    ensure_builtin_tools_registered()
    calls = {"llm": 0}

    async def fake_chat_completion(*, messages, tools=None, **kwargs):
        calls["llm"] += 1
        names = _function_names(tools)
        assert "calculate" not in names
        if calls["llm"] == 1:
            return LLMResponse(
                content="",
                model="test/model",
                tool_calls=[{"id": "calc-guess", "name": "calculate", "arguments": '{"expression":"9*9"}'}],
            )
        tool_messages = [item for item in messages if item.get("role") == "tool"]
        assert tool_messages
        assert '"TOOL_NOT_DISCOVERED"' in tool_messages[-1]["content"]
        return LLMResponse(content="Tool belum ditemukan lewat discovery.", model="test/model")

    monkeypatch.setattr("src.agents.runtime.openrouter_client.chat_completion", fake_chat_completion)
    result = await manager_agent.execute(
        NormalizedMessage(
            message_id="undiscovered-1",
            group_id="group_core_team_01",
            sender_id="user_bima_01",
            text="Halo manager, selamat pagi.",
        )
    )
    assert "Tool belum ditemukan" in result
    assert calls["llm"] == 2


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
async def test_approval_reuse_within_single_agent_run(monkeypatch):
    """P0: Panggilan eksternal identik berulang dalam satu agent run hanya membuat satu approval."""
    calls = {"side_effect": 0, "llm": 0}

    async def fake_send_msg(to: str, text: str):
        calls["side_effect"] += 1
        return {"to": to, "text": text}

    tool_registry.register_tool(
        "send_external_message",
        fake_send_msg,
        domain="messaging",
        capability=ToolCapability.COMMIT,
        risk="high",
        side_effect=True,
        output_trust="external",
        retry_safe=False,
        keywords={"pesan", "message", "kirim"},
    )

    async def fake_chat_completion(*, messages, tools=None, **kwargs):
        calls["llm"] += 1
        if calls["llm"] == 1:
            return LLMResponse(
                content="",
                model="test/model",
                tool_calls=[
                    {"id": "call-1", "name": "send_external_message", "arguments": '{"text":"Halo","to":"bima"}'},
                    {"id": "call-2", "name": "send_external_message", "arguments": '{"text":"Halo","to":"bima"}'},
                ],
            )
        tool_messages = [item for item in messages if item.get("role") == "tool"]
        assert len(tool_messages) == 2
        appr_id1 = json.loads(tool_messages[0]["content"])["approval_id"]
        appr_id2 = json.loads(tool_messages[1]["content"])["approval_id"]
        assert appr_id1 == appr_id2
        return LLMResponse(content="Aksi menunggu persetujuan.", model="test/model")

    monkeypatch.setattr("src.agents.runtime.openrouter_client.chat_completion", fake_chat_completion)
    result = await manager_agent.execute(
        NormalizedMessage(
            message_id="msg-reuse-1",
            group_id="group_reuse_01",
            sender_id="user_bima_01",
            text="Kirim pesan ke bima",
        )
    )
    assert "Aksi menunggu persetujuan" in result
    approvals = await db.fetch_all("SELECT * FROM approvals WHERE group_id='group_reuse_01'")
    assert len(approvals) == 1


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
async def test_unknown_external_result_end_to_end_no_retry():
    """P0: Kegagalan eksternal tidak pasti dicatat unknown, tidak di-retry, dan memblokir re-eksekusi."""
    calls = {"count": 0}

    async def fake_failing_external_action(to: str):
        calls["count"] += 1
        raise UnknownExternalResultError("External provider timed out after request submission")

    tool_registry.register_tool(
        "send_external_message",
        fake_failing_external_action,
        domain="messaging",
        capability=ToolCapability.COMMIT,
        risk="high",
        side_effect=True,
        output_trust="external",
        retry_safe=False,
    )

    request = await approval_gateway.create_request(
        "g_unknown", "send_external_message", {"to": "dest@example.com"}, RoleID.MANAGER
    )
    ok, _ = await approval_gateway.approve_request(request.approval_id, "user1", expected_group_id="g_unknown")
    assert ok is True

    result = await approval_gateway.execute_approved_request(request.approval_id)
    assert result["success"] is False
    assert result["status"] == "unknown"
    assert result["retry_allowed"] is False
    assert calls["count"] == 1

    approval_row = await db.fetch_one("SELECT * FROM approvals WHERE approval_id=?", (request.approval_id,))
    assert approval_row is not None
    assert approval_row["status"] == "unknown"

    exec_row = await db.fetch_one("SELECT * FROM tool_executions WHERE execution_id=?", (result["tool_execution_id"],))
    assert exec_row is not None
    assert exec_row["status"] == "unknown"

    replay = await tool_executor.execute_tool(
        "send_external_message",
        {"to": "dest@example.com"},
        idempotency_key=request.idempotency_key,
        is_approved=True,
    )
    assert replay["success"] is False
    assert replay["error"] == "EXTERNAL_RESULT_UNKNOWN_OR_IN_PROGRESS"
    assert calls["count"] == 1


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


def test_two_task_browser_isolation():
    """P1: Dua task_id berbeda menghasilkan session space terpisah."""
    session1 = AgentBrowserBackend._session_name("task-uuid-1111")
    session2 = AgentBrowserBackend._session_name("task-uuid-2222")
    assert session1 != session2
    assert "task-uuid-1111" in session1
    assert "task-uuid-2222" in session2


@pytest.mark.asyncio
async def test_browser_task_space_cannot_be_injected_by_model(monkeypatch):
    """P0: Argumen _task_space yang disuntikkan model diabaikan dan ditimpa context backend."""
    monkeypatch.setattr(settings, "browser_enabled", True)
    ensure_builtin_tools_registered()
    calls = {"llm": 0, "task_space_used": []}

    async def fake_interact(action, parameters, *, task_space, action_class):
        calls["task_space_used"].append(task_space)
        return {"success": True}

    monkeypatch.setattr("src.browser.tools.agent_browser_backend.interact", fake_interact)

    async def fake_chat_completion(*, messages, tools=None, **kwargs):
        calls["llm"] += 1
        if calls["llm"] == 1:
            return LLMResponse(
                content="",
                model="test/model",
                tool_calls=[
                    {
                        "id": "fill-1",
                        "name": "browser_fill",
                        "arguments": '{"target":"#input","value":"test","_task_space":"injected-evil-space"}',
                    }
                ],
            )
        return LLMResponse(content="Selesai mengisi form.", model="test/model")

    monkeypatch.setattr("src.agents.runtime.openrouter_client.chat_completion", fake_chat_completion)
    await manager_agent.execute(
        NormalizedMessage(
            message_id="msg-inject-1",
            group_id="group_sec_01",
            sender_id="user_bima_01",
            text="Isi form di browser",
        ),
        task_id="legit-task-99",
    )
    assert len(calls["task_space_used"]) == 1
    assert calls["task_space_used"][0] == "task-legit-task-99"
    assert "injected-evil-space" not in calls["task_space_used"][0]


@pytest.mark.asyncio
async def test_missing_browser_binary_fails_gracefully():
    """P1: Executable browser yang tidak ada gagal terkendali tanpa crash sistem."""
    backend = AgentBrowserBackend(executable="definitely_non_existent_binary_12345")
    with pytest.raises(BrowserBackendUnavailableError, match="tidak ditemukan"):
        await backend.open("https://example.com", task_space="task-test")


def test_approval_parameter_canonicalization():
    """P1: Urutan key parameter berbeda diperlakukan identik secara kanonikal."""
    params_a = {"to": "client@example.com", "subject": "Halo", "amount": 100}
    params_b = {"amount": 100, "subject": "Halo", "to": "client@example.com"}
    hash_a = fingerprinter.generate_hash("send_email", params_a)
    hash_b = fingerprinter.generate_hash("send_email", params_b)
    assert hash_a == hash_b
    assert fingerprinter.verify_hash("send_email", params_b, hash_a) is True


@pytest.mark.asyncio
async def test_commit_journal_state_lifecycle():
    """P1: Siklus status jurnal proposal -> approval -> eksekusi terhubung konsisten."""
    async def fake_write(path: str, content: str):
        return {"written": True}

    tool_registry.register_tool(
        "destructive_external_write",
        fake_write,
        domain="storage",
        capability=ToolCapability.COMMIT,
        risk="high",
        side_effect=True,
        output_trust="external",
        retry_safe=False,
    )
    req = await approval_gateway.create_request(
        "g_life", "destructive_external_write", {"content": "data", "path": "/tmp/test"}, RoleID.ADVISOR
    )
    await tool_executor.execute_tool(
        "destructive_external_write",
        {"content": "data", "path": "/tmp/test"},
        is_approved=False,
        approval_id=req.approval_id,
        execution_context={"group_id": "g_life", "role_id": "advisor"},
    )
    j1 = await db.fetch_one("SELECT * FROM tool_executions WHERE approval_id=?", (req.approval_id,))
    assert j1 is not None
    assert j1["status"] == "approval_required"
    assert j1["policy_decision"] == "approval_required"

    ok, _ = await approval_gateway.approve_request(req.approval_id, "admin", expected_group_id="g_life")
    assert ok is True
    res = await approval_gateway.execute_approved_request(req.approval_id)
    assert res["success"] is True

    j2 = await db.fetch_one("SELECT * FROM tool_executions WHERE execution_id=?", (res["tool_execution_id"],))
    assert j2 is not None
    assert j2["status"] == "succeeded"
    assert j2["approval_id"] == req.approval_id


@pytest.mark.asyncio
async def test_provenance_boundary_persistence():
    """P1: Metadata asal data eksternal/untrusted tersimpan pada journal execution."""
    ensure_builtin_tools_registered()

    async def fake_read_att():
        return {"raw": "some untrusted web content"}

    tool_registry.register_tool(
        "read_attachment",
        fake_read_att,
        domain="files",
        capability=ToolCapability.READ,
        output_trust="external",
    )
    res = await tool_executor.execute_tool(
        "read_attachment",
        {},
        execution_context={"group_id": "g_prov", "role_id": "marketing"},
    )
    assert res["success"] is True
    prov = res["provenance"]
    assert prov["trust_class"] == "external"
    assert prov["tainted_fields"] == ["*"]

    row = await db.fetch_one("SELECT * FROM tool_executions WHERE execution_id=?", (res["execution_id"],))
    assert row is not None
    assert row["provenance_json"] is not None
    stored_prov = json.loads(row["provenance_json"])
    assert stored_prov["trust_class"] == "external"


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


@pytest.mark.asyncio
async def test_migration_idempotency_runs_multiple_times_safely(tmp_path):
    """P0: init_schema dijalankan berulang pada database lama tidak menduplikasi baris."""
    path = tmp_path / "legacy_repeat.db"
    conn = sqlite3.connect(path)
    conn.execute(
        """CREATE TABLE tool_executions (idempotency_key TEXT PRIMARY KEY, tool_name TEXT NOT NULL, parameters_json TEXT NOT NULL, status TEXT NOT NULL, result_json TEXT, error_text TEXT, started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, finished_at TIMESTAMP)"""
    )
    conn.execute(
        """INSERT INTO tool_executions (idempotency_key, tool_name, parameters_json, status, result_json) VALUES ('idem-1', 'send_email', '{"to":"user@test.com"}', 'succeeded', '{"ok":true}')"""
    )
    conn.commit()
    conn.close()

    manager = DatabaseManager(str(path))
    try:
        await manager.init_schema()
        count1 = len(await manager.fetch_all("SELECT * FROM tool_executions"))
        assert count1 == 1

        await manager.init_schema()
        count2 = len(await manager.fetch_all("SELECT * FROM tool_executions"))
        assert count2 == 1
        assert await manager.integrity_check() is True
    finally:
        await manager.close()
