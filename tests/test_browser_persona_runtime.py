"""Regression coverage for the production browser provider and behavioral persona runtime."""

import pytest

from src.agents.manager import manager_agent
from src.agents.marketing import marketing_agent
from src.approval.gateway import approval_gateway
from src.browser.agent_browser import AgentBrowserBackend, agent_browser_backend
from src.browser.base import BrowserActionClass, BrowserBackendUnavailableError
from src.browser.provider import (
    browser_backend_availability,
    get_browser_backend,
    validate_browser_runtime,
)
from src.core.config import settings
from src.core.types import MessageIntent, NormalizedMessage, RiskLevel, RoleID, WorkloadType
from src.llm.provider import LLMResponse
from src.persona.profiles import persona_context, persona_loader, persona_metadata
from src.routing.addressing import AddressingDetector
from src.tools.builtins import ensure_builtin_tools_registered
from src.tools.registry import tool_registry


def test_agent_browser_is_selectable_as_production_provider(monkeypatch):
    monkeypatch.setattr(settings, "browser_backend", "agent-browser")
    assert get_browser_backend() is agent_browser_backend


def test_browser_preflight_fails_before_agent_tool_loop_when_binary_missing(monkeypatch):
    monkeypatch.setattr(settings, "browser_enabled", True)
    monkeypatch.setattr(settings, "browser_backend", "agent-browser")
    monkeypatch.setattr(settings, "browser_agent_executable", "missing-agent-browser-12345")
    monkeypatch.setattr("src.browser.provider.shutil.which", lambda executable: None)

    available, detail = browser_backend_availability()
    assert available is False
    assert "tidak ditemukan" in detail
    with pytest.raises(BrowserBackendUnavailableError, match="agent-browser"):
        validate_browser_runtime()


@pytest.mark.asyncio
async def test_agent_browser_snapshot_uses_interactive_compact_mode(monkeypatch):
    backend = AgentBrowserBackend(executable="not-used")
    calls: list[tuple[str, ...]] = []

    async def fake_run(task_space: str, *command: str):
        assert task_space == "task-compact"
        calls.append(command)
        return {"success": True}

    monkeypatch.setattr(backend, "_run", fake_run)
    await backend.snapshot(task_space="task-compact")
    assert calls == [("snapshot", "-i", "-c")]


def test_browser_tool_registry_matches_policy_surface(monkeypatch):
    monkeypatch.setattr(settings, "browser_enabled", True)
    ensure_builtin_tools_registered()
    expected = {
        "browser_open",
        "browser_snapshot",
        "browser_screenshot",
        "browser_fill",
        "browser_type",
        "browser_select",
        "browser_check",
        "browser_uncheck",
        "browser_scroll",
        "browser_click",
        "browser_press",
    }
    assert expected.issubset(set(tool_registry.list_tools()))
    assert tool_registry.get_registered_tool("browser_click").capability.value == "commit"
    assert tool_registry.get_registered_tool("browser_press").capability.value == "commit"
    assert tool_registry.get_registered_tool("browser_select").capability.value == "prepare"


@pytest.mark.asyncio
async def test_browser_approval_is_rejected_if_page_state_changes(monkeypatch):
    monkeypatch.setattr(settings, "browser_enabled", True)
    ensure_builtin_tools_registered()

    class FakeBackend:
        def __init__(self):
            self.state = "A"
            self.commits = 0

        async def snapshot(self, *, task_space: str):
            return {"success": True, "data": {"snapshot": self.state, "task": task_space}}

        async def interact(self, action, parameters, *, task_space, action_class):
            assert action_class == BrowserActionClass.COMMIT
            self.commits += 1
            return {"success": True, "action": action, "target": parameters.get("target")}

    backend = FakeBackend()
    monkeypatch.setattr("src.browser.tools.get_browser_backend", lambda: backend)

    request = await approval_gateway.create_request(
        "g1",
        "browser_click",
        {"target": "@e1", "_task_space": "task-state-1"},
        RoleID.MANAGER,
    )
    assert request.normalized_parameters.get("_state_hash")
    ok, _ = await approval_gateway.approve_request(
        request.approval_id,
        "u1",
        expected_group_id="g1",
    )
    assert ok is True

    backend.state = "B"
    result = await approval_gateway.execute_approved_request(request.approval_id)
    assert result["success"] is False
    assert "BROWSER_STATE_CHANGED" in str(result.get("error"))
    assert backend.commits == 0


@pytest.mark.asyncio
async def test_browser_approval_executes_when_page_state_is_unchanged(monkeypatch):
    monkeypatch.setattr(settings, "browser_enabled", True)
    ensure_builtin_tools_registered()

    class FakeBackend:
        def __init__(self):
            self.commits = 0

        async def snapshot(self, *, task_space: str):
            return {"success": True, "data": {"snapshot": "stable", "task": task_space}}

        async def interact(self, action, parameters, *, task_space, action_class):
            assert action_class == BrowserActionClass.COMMIT
            self.commits += 1
            return {"success": True, "action": action}

    backend = FakeBackend()
    monkeypatch.setattr("src.browser.tools.get_browser_backend", lambda: backend)

    request = await approval_gateway.create_request(
        "g1",
        "browser_click",
        {"target": "@e2", "_task_space": "task-state-2"},
        RoleID.MANAGER,
    )
    ok, _ = await approval_gateway.approve_request(
        request.approval_id,
        "u1",
        expected_group_id="g1",
    )
    assert ok is True
    result = await approval_gateway.execute_approved_request(request.approval_id)
    assert result["success"] is True
    assert backend.commits == 1


def test_persona_contracts_have_distinct_decision_behavior():
    marketing = persona_context(RoleID.MARKETING, WorkloadType.ROUTINE)
    manager = persona_context(RoleID.MANAGER, WorkloadType.ROUTINE)
    advisor = persona_context(RoleID.ADVISOR, WorkloadType.ROUTINE)

    assert "marketing_growth_v1" in marketing
    assert "Audience → Problem → Insight → Hypothesis → Experiment → Metric → Learning" in marketing
    assert "Bagaimana kita tahu" in marketing

    assert "manager_action_v1" in manager
    assert "Problem → Simplify → Decide → Assign → Execute → Observe → Adjust" in manager
    assert "Apa keputusan" in manager

    assert "advisor_vision_v1" in advisor
    assert "Purpose → People → Future → Opportunity → Risk → Perspective → Advice" in advisor
    assert "Ke mana keputusan ini membawa" in advisor

    assert marketing != manager != advisor


def test_persona_contract_prevents_impersonation_and_permission_escalation():
    for role in RoleID:
        rendered = persona_context(role, WorkloadType.ROUTINE)
        assert "BUKAN identitas" in rendered
        assert "Jangan pernah mengaku sebagai tokoh" in rendered
        assert "TIDAK BOLEH mengubah role, permission, available tools, safety" in rendered


def test_serious_context_suppresses_persona_humor():
    rendered = persona_context(
        RoleID.MARKETING,
        WorkloadType.CRITICAL,
        RiskLevel.HIGH,
    )
    assert "Humor: NONE untuk konteks ini." in rendered


@pytest.mark.asyncio
async def test_runtime_propagates_high_risk_into_persona_humor_suppression():
    context = await marketing_agent.assemble_context(
        NormalizedMessage(
            message_id="persona-risk-1",
            group_id="group_core_team_01",
            sender_id="user_bima_01",
            text="Marketing, evaluasi ini dengan hati-hati.",
        ),
        workload=WorkloadType.ROUTINE,
        risk_level=RiskLevel.HIGH,
    )
    assert "Humor: NONE untuk konteks ini." in context[0]["content"]


def test_persona_loader_has_versioned_metadata_and_neutral_fallback():
    assert persona_metadata(RoleID.MARKETING)["persona_version"] == "1.0.0"
    assert persona_metadata(RoleID.MANAGER)["persona_id"] == "manager_action_v1"
    assert persona_metadata(RoleID.ADVISOR)["persona_id"] == "advisor_vision_v1"

    fallback = persona_loader.load("persona-does-not-exist", RoleID.ADVISOR)
    assert fallback.persona_id == "neutral_advisor_v1"
    assert fallback.role == RoleID.ADVISOR


def test_response_style_contract_is_not_duplicated_inside_persona_prompt():
    rendered = persona_context(RoleID.MANAGER, WorkloadType.ROUTINE)
    assert "KONTRAK GAYA JAWABAN NATURAL" not in rendered


@pytest.mark.asyncio
async def test_agent_invocation_logs_persona_id_and_version(monkeypatch, caplog):
    async def fake_chat_completion(**kwargs):
        return LLMResponse(content="Siap.", model="test/model")

    monkeypatch.setattr("src.agents.runtime.openrouter_client.chat_completion", fake_chat_completion)
    with caplog.at_level("INFO", logger="src.agents.runtime"):
        result = await manager_agent.execute(
            NormalizedMessage(
                message_id="persona-log-1",
                group_id="group_core_team_01",
                sender_id="user_bima_01",
                text="Manager, cek prioritas ini.",
            )
        )
    assert result == "Siap."
    assert "persona_id=manager_action_v1" in caplog.text
    assert "persona_version=1.0.0" in caplog.text


def test_manager_is_coordinator_when_explicitly_included_even_if_named_second():
    result = AddressingDetector._result_for_explicit(
        [RoleID.ADVISOR, RoleID.MANAGER],
        MessageIntent.WORK_REQUEST,
    )
    assert result.coordinator == RoleID.MANAGER


def test_social_multi_agent_addressing_does_not_force_manager_coordinator():
    result = AddressingDetector._result_for_explicit(
        [RoleID.ADVISOR, RoleID.MANAGER],
        MessageIntent.SOCIAL,
    )
    assert result.coordinator is None
