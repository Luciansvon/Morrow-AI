"""Regression tests for failures observed in live Telegram acceptance testing."""

import json
from datetime import date

import pytest

from src.adapters.cli import CLIAdapter
from src.agents.advisor import advisor_agent
from src.agents.manager import manager_agent
from src.core.config import settings
from src.core.orchestrator import SystemOrchestrator
from src.core.types import NormalizedMessage, RoleID
from src.llm.provider import LLMResponse
from src.memory.judge import MemoryJudge
from src.memory.service import memory_service
from src.tasks.service import task_service
from src.tools.builtins import current_datetime


def _server_tool_types(tools: list[dict]) -> set[str]:
    return {
        str(tool.get("type"))
        for tool in tools
        if str(tool.get("type", "")).startswith("openrouter:")
    }


def test_explicit_browser_automation_cannot_fall_back_to_web_fetch(monkeypatch):
    monkeypatch.setattr(settings, "browser_enabled", False)
    browser_tools = manager_agent.available_tools(
        "Manager, gunakan browser automation Morrow untuk buka form lalu isi field nama."
    )
    assert "openrouter:web_fetch" not in _server_tool_types(browser_tools)
    assert "openrouter:web_search" not in _server_tool_types(browser_tools)

    normal_web_tools = manager_agent.available_tools(
        "Baca URL https://example.com dan rangkum isi halamannya."
    )
    assert "openrouter:web_fetch" in _server_tool_types(normal_web_tools)


@pytest.mark.asyncio
async def test_final_context_locks_role_and_paragraph_mode_for_ordinary_reply():
    message = NormalizedMessage(
        message_id="live-role-lock-1",
        group_id="group_core_team_01",
        sender_id="user_bima_01",
        text="Advisor, menurut kamu fokus email dulu masuk akal nggak?",
    )
    context = await advisor_agent.assemble_context(message)
    system = context[0]["content"]
    assert "ROLE AKTIF TERKUNCI: ADVISOR" in system
    assert "jangan mengaku sebagai coordinator" in system
    assert "FORMAT WAJIB untuk respons ini: tulis sebagai 1-5 paragraf natural" in system
    assert "Jangan gunakan heading Markdown, bullet list, numbered list" in system
    assert system.rfind("KONTRAK OUTPUT FINAL") > system.rfind("TUGAS AKTIF SAYA")


@pytest.mark.asyncio
async def test_explicit_structured_request_keeps_structure_available():
    message = NormalizedMessage(
        message_id="live-structured-1",
        group_id="group_core_team_01",
        sender_id="user_bima_01",
        text="Manager, buat checklist 5 langkah buat audit deployment.",
    )
    context = await manager_agent.assemble_context(message)
    system = context[0]["content"]
    assert "Pengguna meminta struktur eksplisit" in system


@pytest.mark.asyncio
async def test_task_context_isolated_to_current_collaboration_task():
    email_task = await task_service.create_task(
        group_id="group_core_team_01",
        title="Evaluasi prioritas integrasi email Morrow",
        description="Nilai effort, dependency, risiko, dan trade-off integrasi email.",
        initial_owner=RoleID.MANAGER,
    )
    await task_service.create_task(
        group_id="group_core_team_01",
        title="Riset kompetitor Etsy gantungan kunci kayu",
        description="Analisis listing dan positioning produk kayu di Etsy.",
        initial_owner=RoleID.ADVISOR,
    )
    message = NormalizedMessage(
        message_id="live-task-isolation-1",
        group_id="group_core_team_01",
        sender_id="user_bima_01",
        text="Advisor, berikan analisis teknis untuk keputusan email ini.",
    )
    context = await advisor_agent.assemble_context(message, task_id=email_task.id)
    system = context[0]["content"]
    assert "Evaluasi prioritas integrasi email Morrow" in system
    assert "Riset kompetitor Etsy gantungan kunci kayu" not in system


@pytest.mark.asyncio
async def test_multi_agent_work_actually_invokes_advisor(monkeypatch):
    orchestrator = SystemOrchestrator(CLIAdapter())
    calls: list[RoleID] = []

    async def fake_execute(message, role, **kwargs):
        calls.append(role)
        return f"kontribusi {role.value}"

    monkeypatch.setattr(orchestrator, "_execute_agent", fake_execute)
    result = await orchestrator.handle_incoming_message(
        NormalizedMessage(
            message_id="live-collab-1",
            group_id="group_core_team_01",
            sender_id="user_bima_01",
            text="Manager dan Advisor, bantu nilai apakah integrasi email layak diprioritaskan.",
        )
    )
    assert result is not None
    assert calls[:2] == [RoleID.MANAGER, RoleID.ADVISOR]
    assert RoleID.MARKETING not in calls


@pytest.mark.asyncio
@pytest.mark.parametrize("alias", ["Jakarta", "jakarta, indonesia", "WIB", "UTC+7"])
async def test_current_datetime_accepts_common_jakarta_aliases(alias):
    result = await current_datetime(alias)
    parsed = date.fromisoformat(str(result["date"]))
    assert result["timezone"] == "Asia/Jakarta"
    assert result["weekday_index"] == parsed.weekday()
    assert result["weekday"] == ("Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu")[parsed.weekday()]


@pytest.mark.asyncio
async def test_memory_judge_rejects_assistant_only_numeric_market_claim(monkeypatch):
    async def fake_chat_completion(**kwargs):
        return LLMResponse(
            content=json.dumps(
                {
                    "should_store": True,
                    "items": [
                        {
                            "scope": "shared",
                            "key": "etsy_handmade_wood_share",
                            "value": "73% pembeli Etsy mencari handmade wood",
                            "memory_type": "fact",
                            "reason": "hasil riset agent",
                        }
                    ],
                }
            ),
            model="test/model",
        )

    monkeypatch.setattr("src.memory.judge.openrouter_client.chat_completion", fake_chat_completion)
    result = await MemoryJudge.evaluate_and_commit(
        actor_id="user_bima_01",
        role_id=RoleID.MARKETING,
        group_id="group_core_team_01",
        user_text="Marketing, cari tren Etsy terbaru untuk produk handmade kayu.",
        assistant_text="73% pembeli Etsy mencari handmade wood.",
    )
    assert result is not None
    assert result["stored_count"] == 0
    recalled = await memory_service.retrieve_relevant_memory(
        "73 persen pembeli Etsy handmade wood",
        RoleID.MARKETING,
        "group_core_team_01",
    )
    assert not any(row["key"] == "etsy_handmade_wood_share" for row in recalled)


@pytest.mark.asyncio
async def test_memory_judge_rejects_assistant_only_architecture_claim(monkeypatch):
    async def fake_chat_completion(**kwargs):
        return LLMResponse(
            content=json.dumps(
                {
                    "should_store": True,
                    "items": [
                        {
                            "scope": "shared",
                            "key": "runtime_architecture",
                            "value": "Morrow berjalan di OpenClaw pada AWS",
                            "memory_type": "fact",
                            "reason": "assistant inferred architecture",
                        }
                    ],
                }
            ),
            model="test/model",
        )

    monkeypatch.setattr("src.memory.judge.openrouter_client.chat_completion", fake_chat_completion)
    result = await MemoryJudge.evaluate_and_commit(
        actor_id="user_bima_01",
        role_id=RoleID.ADVISOR,
        group_id="group_core_team_01",
        user_text="Advisor, analisis kalau Morrow dipakai 20 user sekaligus.",
        assistant_text="Morrow berjalan di OpenClaw pada AWS.",
    )
    assert result is not None
    assert result["stored_count"] == 0


@pytest.mark.asyncio
async def test_memory_judge_accepts_fact_supported_by_user(monkeypatch):
    async def fake_chat_completion(**kwargs):
        return LLMResponse(
            content=json.dumps(
                {
                    "should_store": True,
                    "items": [
                        {
                            "scope": "shared",
                            "key": "target_market",
                            "value": "target pasar luar negeri",
                            "memory_type": "fact",
                            "reason": "stated by user",
                        }
                    ],
                }
            ),
            model="test/model",
        )

    monkeypatch.setattr("src.memory.judge.openrouter_client.chat_completion", fake_chat_completion)
    result = await MemoryJudge.evaluate_and_commit(
        actor_id="user_bima_01",
        role_id=RoleID.MARKETING,
        group_id="group_core_team_01",
        user_text="Target pasar produk ini buyer luar negeri.",
        assistant_text="Saya akan membuat strategi untuk buyer luar negeri.",
    )
    assert result is not None
    assert result["stored_count"] == 1
    assert result["stored_items"][0]["key"] == "target_market"


@pytest.mark.asyncio
async def test_evidence_contract_requires_traceable_sources_for_external_numbers():
    message = NormalizedMessage(
        message_id="live-evidence-1",
        group_id="group_core_team_01",
        sender_id="user_bima_01",
        text="Marketing, cari tren Etsy terbaru untuk handmade wood.",
    )
    context = await manager_agent.assemble_context(message)
    system = context[0]["content"]
    assert "setiap angka eksternal yang disajikan sebagai fakta harus dapat ditelusuri" in system
    assert "Memori jangka panjang bukan bukti eksternal yang otomatis valid" in system
