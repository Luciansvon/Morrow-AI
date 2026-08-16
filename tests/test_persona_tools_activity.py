"""Regression coverage for persona, tool runtime, and Telegram-style activity lifecycle."""

import pytest

from src.adapters.cli import CLIAdapter
from src.agents.advisor import advisor_agent
from src.agents.manager import manager_agent
from src.agents.marketing import marketing_agent
from src.core.orchestrator import SystemOrchestrator
from src.core.types import NormalizedMessage, RiskLevel, RoleID, WorkloadType
from src.llm.provider import LLMResponse
from src.persona.profiles import persona_context
from src.routing.intent import intent_detector
from src.routing.social import is_fast_social
from src.tools.builtins import calculate, current_datetime


def test_personas_are_role_specific_and_keep_identity_honest():
    manager = persona_context(RoleID.MANAGER, WorkloadType.CASUAL)
    marketing = persona_context(RoleID.MARKETING, WorkloadType.CASUAL)
    advisor = persona_context(RoleID.ADVISOR, WorkloadType.CASUAL)

    assert "manager_action_v1" in manager
    assert "Pragmatic Action Manager" in manager
    assert "Bob Sadino" in manager

    assert "marketing_growth_v1" in marketing
    assert "Technical Growth Strategist" in marketing
    assert "Dharmesh Shah" in marketing

    assert "advisor_vision_v1" in advisor
    assert "Visionary Humanist Advisor" in advisor
    assert "Jack Ma" in advisor

    for prompt in (manager, marketing, advisor):
        assert "BUKAN identitas" in prompt
        assert "Jangan pernah mengaku sebagai tokoh" in prompt
        assert "Jangan mengarang pengalaman pribadi" in prompt
        assert "agent AI Morrow" in prompt


@pytest.mark.asyncio
async def test_response_style_rules_are_injected_once_in_final_runtime_contract():
    """Paragraph-first stays global without duplicating the same rules inside persona prompts."""
    agents = {
        RoleID.MANAGER: manager_agent,
        RoleID.MARKETING: marketing_agent,
        RoleID.ADVISOR: advisor_agent,
    }
    for role, agent in agents.items():
        persona = persona_context(role, WorkloadType.ROUTINE)
        assert "Default Telegram adalah paragraf natural" not in persona

        context = await agent.assemble_context(
            NormalizedMessage(
                message_id=f"style-once-{role.value}",
                group_id="group_core_team_01",
                sender_id="user_bima_01",
                text=f"{role.value}, review keputusan ini secara singkat",
            )
        )
        system = context[0]["content"]
        assert system.count("Default Telegram adalah paragraf natural") == 1
        assert system.count("Kekuatan / Kekurangan / Saran / Pertanyaan") == 1
        assert system.count("Default-nya tanpa **bold**") == 1
        assert system.count("biru, ungu, gradient, glow, sparkle, atau neon") == 1
        assert system.count("Apakah mau saya...") == 1
        assert system.count("paling banyak satu daftar") == 1


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
    assert "openrouter:datetime" not in tool_types


@pytest.mark.asyncio
async def test_current_datetime_weekday_is_consistent_with_date():
    result = await current_datetime("Asia/Jakarta")
    from datetime import date

    weekday_id = ("Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu")
    parsed = date.fromisoformat(result["date"])
    assert result["weekday"] == weekday_id[parsed.weekday()]
    assert result["weekday_index"] == parsed.weekday()
    assert result["timezone"] == "Asia/Jakarta"
    assert "iso" in result
    assert "time" in result
    assert "utc_offset" in result

    # Invariant: 2026-08-16 is Sunday / Minggu with index 6
    test_date = date(2026, 8, 16)
    assert weekday_id[test_date.weekday()] == "Minggu"
    assert test_date.weekday() == 6


@pytest.mark.asyncio
async def test_final_output_contract_is_after_skills_memory_and_handoff(monkeypatch):
    async def no_memory(*args, **kwargs):
        return []

    async def no_tasks(*args, **kwargs):
        return []

    monkeypatch.setattr("src.agents.runtime.memory_service.retrieve_relevant_memory", no_memory)
    monkeypatch.setattr("src.agents.runtime.task_service.list_active_tasks", no_tasks)
    context = await manager_agent.assemble_context(
        NormalizedMessage(
            message_id="style-order-1",
            group_id="group_core_team_01",
            sender_id="user_bima_01",
            text="review logo ini",
        ),
        handoff_payload={"mode": "test"},
    )
    system = context[0]["content"]
    final_pos = system.rfind("KONTRAK OUTPUT FINAL (INSTRUKSI TERAKHIR)")
    assert final_pos > system.rfind("KEAHLIAN YANG TERSEDIA")
    assert final_pos > system.rfind("MEMORI JANGKA PANJANG RELEVAN")
    assert final_pos > system.rfind("KONTEKS HANDOFF TERSTRUKTUR")
    assert "Fakta eksternal yang mudah berubah" in system[final_pos:]
    assert "Default-nya tanpa **bold**" in system[final_pos:]


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
    assert result == "[manager]: lah lu yang mulai wkwk"
    assert seen["workload"] == WorkloadType.CASUAL
    assert seen["risk_level"] == RiskLevel.LOW
