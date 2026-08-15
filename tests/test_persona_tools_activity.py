"""Regression coverage for persona, tool runtime, and Telegram-style activity lifecycle."""

import pytest

from src.adapters.cli import CLIAdapter
from src.agents.manager import manager_agent
from src.core.orchestrator import SystemOrchestrator
from src.core.types import NormalizedMessage, RiskLevel, RoleID, WorkloadType
from src.llm.provider import LLMResponse
from src.persona.profiles import persona_context
from src.routing.intent import intent_detector
from src.routing.social import is_fast_social
from src.tools.builtins import calculate


def test_personas_are_role_specific_and_keep_identity_honest():
    manager = persona_context(RoleID.MANAGER, WorkloadType.CASUAL)
    marketing = persona_context(RoleID.MARKETING, WorkloadType.CASUAL)
    advisor = persona_context(RoleID.ADVISOR, WorkloadType.CASUAL)

    assert "Millennial Indonesia" in manager
    assert "Gen Z Indonesia" in marketing
    assert "Boomer-inspired" in advisor
    for prompt in (manager, marketing, advisor):
        assert "Jika pengguna bertanya langsung apakah kamu manusia/bot/AI" in prompt
        assert "Jangan mengarang pengalaman fisik" in prompt


def test_fast_social_only_covers_simple_greetings():
    assert is_fast_social("halo semua") is True
    assert is_fast_social("pagi tim") is True
    assert is_fast_social("Manager, halo") is True
    assert is_fast_social("Manager dan Marketing, halo") is True
    assert is_fast_social("wkwkwk lu kocak") is False
    assert intent_detector.detect_intent("wkwkwk lu kocak").value == "social"
    assert intent_detector.detect_intent("anjir harga ini berapa?").value == "question"


@pytest.mark.asyncio
async def test_safe_calculator_rejects_code_execution():
    assert (await calculate("(12500 * 3) + 4500"))["result"] == 42000
    with pytest.raises(ValueError):
        await calculate("__import__('os').system('echo nope')")


@pytest.mark.asyncio
async def test_agent_tool_loop_executes_registered_calculator(monkeypatch):
    calls = {"count": 0, "tools": None}

    async def fake_chat_completion(*, messages, tools=None, **kwargs):
        calls["count"] += 1
        calls["tools"] = tools
        if calls["count"] == 1:
            return LLMResponse(
                content="",
                model="test/model",
                tool_calls=[
                    {
                        "id": "call_calc",
                        "name": "calculate",
                        "arguments": '{"expression":"7*6"}',
                    }
                ],
            )
        assert any(
            msg.get("role") == "tool" and '"result": 42' in msg.get("content", "")
            for msg in messages
        )
        return LLMResponse(content="42", model="test/model")

    monkeypatch.setattr(
        "src.agents.runtime.openrouter_client.chat_completion",
        fake_chat_completion,
    )
    result = await manager_agent.execute(
        NormalizedMessage(
            message_id="tool-loop-1",
            group_id="group_core_team_01",
            sender_id="user_bima_01",
            text="Manager, hitung 7*6",
        )
    )
    assert result == "42"
    assert calls["count"] == 2
    tool_types = {tool.get("type") for tool in calls["tools"]}
    assert "function" in tool_types
    assert "openrouter:web_search" in tool_types
    assert "openrouter:web_fetch" in tool_types
    assert "openrouter:datetime" in tool_types


class ActivityCaptureAdapter(CLIAdapter):
    def __init__(self):
        super().__init__()
        self.activities: list[tuple] = []

    async def begin_activity(self, group_id, text, from_role, reply_to_message_id=None):
        self.activities.append(("begin", from_role, text, reply_to_message_id))
        return "activity-1"

    async def end_activity(self, group_id, activity_id, from_role):
        self.activities.append(("end", from_role, activity_id))


class FakeAgent:
    async def execute(self, message, **kwargs):
        return "udah, gue susun."


@pytest.mark.asyncio
async def test_orchestrator_wraps_agent_work_with_activity_preview(monkeypatch):
    adapter = ActivityCaptureAdapter()
    orchestrator = SystemOrchestrator(adapter)
    orchestrator._agents[RoleID.MANAGER] = FakeAgent()

    async def no_memory(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "src.core.orchestrator.memory_judge.evaluate_and_commit",
        no_memory,
    )
    result = await orchestrator.handle_incoming_message(
        NormalizedMessage(
            message_id="activity-work-1",
            group_id="group_core_team_01",
            sender_id="user_bima_01",
            text="Manager, buat rencana singkat",
        )
    )
    assert result == "udah, gue susun."
    assert adapter.activities[0][0] == "begin"
    assert adapter.activities[-1] == ("end", RoleID.MANAGER, "activity-1")


@pytest.mark.asyncio
async def test_rich_social_banter_uses_persona_runtime(monkeypatch):
    adapter = ActivityCaptureAdapter()
    orchestrator = SystemOrchestrator(adapter)
    seen = {}

    class SocialAgent:
        async def execute(self, message, **kwargs):
            seen.update(kwargs)
            return "lah lu yang mulai wkwk"

    orchestrator._agents[RoleID.MANAGER] = SocialAgent()
    result = await orchestrator.handle_incoming_message(
        NormalizedMessage(
            message_id="social-rich-1",
            group_id="group_core_team_01",
            sender_id="user_bima_01",
            text="Manager, wkwkwk lu kocak",
        )
    )
    assert result == "lah lu yang mulai wkwk"
    assert seen["workload"] == WorkloadType.CASUAL
    assert seen["risk_level"] == RiskLevel.LOW
