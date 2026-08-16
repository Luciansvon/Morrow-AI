"""Regression coverage for failures found by manual Telegram smoke testing."""

import pytest

from src.adapters.cli import CLIAdapter
from src.agents.manager import manager_agent
from src.core.orchestrator import SystemOrchestrator
from src.core.types import NormalizedMessage, RoleID
from src.llm.provider import LLMResponse
from src.memory.service import memory_service
from src.tools.registry import ToolCapability, tool_registry


@pytest.mark.asyncio
async def test_explicit_memory_command_is_durably_written_before_ack():
    orchestrator = SystemOrchestrator(CLIAdapter())
    text = (
        "Manager, catat sebagai keputusan: browser Morrow tetap provider-neutral "
        "dan tindakan COMMIT harus minta approval user."
    )
    result = await orchestrator.handle_incoming_message(
        NormalizedMessage(
            message_id="memory-explicit-1",
            group_id="group_core_team_01",
            sender_id="user_bima_01",
            text=text,
        )
    )
    assert result is not None
    assert result.startswith("Sudah dicatat ke memori bersama sebagai keputusan:")

    recalled = await memory_service.retrieve_relevant_memory(
        "keputusan browser dan COMMIT approval",
        RoleID.MANAGER,
        "group_core_team_01",
    )
    assert any("provider-neutral" in row["value"] and "COMMIT" in row["value"] for row in recalled)
    assert any(row["memory_type"] == "decision" for row in recalled)


@pytest.mark.asyncio
async def test_explicit_memory_command_never_false_confirms_failed_write(monkeypatch):
    orchestrator = SystemOrchestrator(CLIAdapter())

    async def fail_write(*args, **kwargs):
        raise RuntimeError("disk unavailable")

    monkeypatch.setattr("src.core.orchestrator.memory_judge.commit_explicit_directive", fail_write)
    result = await orchestrator.handle_incoming_message(
        NormalizedMessage(
            message_id="memory-explicit-fail-1",
            group_id="group_core_team_01",
            sender_id="user_bima_01",
            text="Manager, catat sebagai keputusan: jangan auto-submit browser form.",
        )
    )
    assert result is not None
    assert result.startswith("Belum tersimpan.")
    assert "Sudah dicatat" not in result


@pytest.mark.asyncio
async def test_repeated_identical_browser_failure_stops_before_max_tool_rounds(monkeypatch):
    async def broken_browser_probe(target: str):
        raise ValueError("Browser target/context belum tersedia")

    tool_registry.register_tool(
        "browser_probe",
        broken_browser_probe,
        description="Probe browser context untuk test.",
        parameters={
            "type": "object",
            "properties": {"target": {"type": "string"}},
            "required": ["target"],
            "additionalProperties": False,
        },
        domain="browser",
        capability=ToolCapability.READ,
        risk="low",
        side_effect=False,
        output_trust="external",
        retry_safe=False,
        keywords={"browser", "form", "probe"},
    )
    calls = {"llm": 0}

    async def fake_chat_completion(*, messages, tools=None, **kwargs):
        calls["llm"] += 1
        if calls["llm"] <= 2:
            return LLMResponse(
                content="",
                model="test/model",
                tool_calls=[
                    {
                        "id": f"probe-{calls['llm']}",
                        "name": "browser_probe",
                        "arguments": '{"target":"missing"}',
                    }
                ],
            )
        raise AssertionError("runtime seharusnya berhenti sebelum putaran ketiga")

    monkeypatch.setattr("src.agents.runtime.openrouter_client.chat_completion", fake_chat_completion)
    result = await manager_agent.execute(
        NormalizedMessage(
            message_id="browser-loop-break-1",
            group_id="group_core_team_01",
            sender_id="user_bima_01",
            text="Manager, isi form browser ini tapi konteksnya belum ada.",
        )
    )
    assert "tidak akan mengulangnya tanpa informasi baru" in result
    assert calls["llm"] == 2
