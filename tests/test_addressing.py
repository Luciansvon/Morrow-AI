"""Pengujian Fitur Collective & Multi-Agent Addressing dan Intent System."""

from typing import Any

import pytest

from src.core.orchestrator import SystemOrchestrator
from src.core.types import AddressingType, MessageIntent, NormalizedMessage, RoleID
from src.routing.addressing import addressing_detector
from src.routing.social import social_response
from src.tasks.service import task_service


class MockChannelAdapter:
    """Mock Adapter perpesanan untuk pengujian multi-response."""

    def __init__(self):
        self.sent_messages = []

    def register_handler(self, handler):
        self.handler = handler

    async def start(self):
        pass

    async def stop(self):
        pass

    async def send_message(self, group_id: str, text: str, from_role: RoleID | None = None, reply_to_message_id: str | None = None) -> str:
        role_val = from_role.value if from_role else "manager"
        msg_id = f"mock_sent_{role_val}_{len(self.sent_messages)+1}"
        self.sent_messages.append({
            "msg_id": msg_id,
            "group_id": group_id,
            "text": text,
            "from_role": role_val,
            "reply_to": reply_to_message_id,
        })
        return msg_id

    async def send_approval_prompt(self, group_id: str, approval_id: str, action_description: str, parameters: dict[str, Any]):
        pass


@pytest.fixture
def mock_adapter():
    return MockChannelAdapter()


@pytest.fixture
def orchestrator(mock_adapter):
    return SystemOrchestrator(mock_adapter)


@pytest.mark.asyncio
async def test_halo_semua_triggers_all_three_agents(orchestrator, mock_adapter):
    """1. 'halo semua' -> all 3 agents (Social Broadcast Mode A)."""
    msg = NormalizedMessage(
        message_id="msg_social_01",
        group_id="group_core_team_01",
        sender_id="user_bima_01",
        text="halo semua",
    )
    res = await addressing_detector.detect(msg)
    assert res.addressing_type == AddressingType.ALL_AGENTS
    assert res.intent == MessageIntent.SOCIAL
    assert set(res.target_agents) == {RoleID.MANAGER, RoleID.MARKETING, RoleID.ADVISOR}

    await orchestrator.handle_incoming_message(msg)
    # Tiga bot harus membalas
    assert len(mock_adapter.sent_messages) == 3
    roles_sent = {m["from_role"] for m in mock_adapter.sent_messages}
    assert roles_sent == {"manager", "marketing", "advisor"}


@pytest.mark.asyncio
async def test_pagi_semua_triggers_all_three_agents():
    """2. 'pagi semua' -> all 3 agents."""
    msg = NormalizedMessage(message_id="m2", group_id="g1", sender_id="u1", text="pagi semua")
    res = await addressing_detector.detect(msg)
    assert res.addressing_type == AddressingType.ALL_AGENTS
    assert res.intent == MessageIntent.SOCIAL


@pytest.mark.asyncio
async def test_hai_tim_triggers_all_three_agents():
    """3. 'hai tim' -> all 3 agents."""
    msg = NormalizedMessage(message_id="m3", group_id="g1", sender_id="u1", text="hai tim")
    res = await addressing_detector.detect(msg)
    assert res.addressing_type == AddressingType.ALL_AGENTS
    assert res.intent == MessageIntent.SOCIAL


@pytest.mark.asyncio
async def test_kalian_gimana_triggers_all_three_agents():
    """4. 'kalian gimana?' -> all 3 agents."""
    msg = NormalizedMessage(message_id="m4", group_id="g1", sender_id="u1", text="kalian gimana?")
    res = await addressing_detector.detect(msg)
    assert res.addressing_type == AddressingType.ALL_AGENTS
    assert res.intent == MessageIntent.SOCIAL


@pytest.mark.asyncio
async def test_manager_dan_marketing_halo_triggers_two_agents_only(orchestrator, mock_adapter):
    """5. 'Manager dan Marketing, halo' -> Manager + Marketing only (Social)."""
    msg = NormalizedMessage(
        message_id="msg_two_01",
        group_id="group_core_team_01",
        sender_id="user_bima_01",
        text="Manager dan Marketing, halo",
    )
    res = await addressing_detector.detect(msg)
    assert res.addressing_type == AddressingType.MULTIPLE_AGENTS
    assert set(res.target_agents) == {RoleID.MANAGER, RoleID.MARKETING}
    assert res.intent == MessageIntent.SOCIAL

    await orchestrator.handle_incoming_message(msg)
    # Tepat 2 bot yang membalas (Manager & Marketing)
    assert len(mock_adapter.sent_messages) == 2
    roles_sent = {m["from_role"] for m in mock_adapter.sent_messages}
    assert roles_sent == {"manager", "marketing"}


@pytest.mark.asyncio
async def test_manager_halo_triggers_manager_only(orchestrator, mock_adapter):
    """6. 'Manager, halo' -> Manager only."""
    msg = NormalizedMessage(
        message_id="msg_single_01",
        group_id="group_core_team_01",
        sender_id="user_bima_01",
        text="Manager, halo",
    )
    res = await addressing_detector.detect(msg)
    assert res.addressing_type == AddressingType.SINGLE_AGENT
    assert res.target_agents == [RoleID.MANAGER]

    await orchestrator.handle_incoming_message(msg)
    assert len(mock_adapter.sent_messages) == 1
    assert mock_adapter.sent_messages[0]["from_role"] == "manager"


@pytest.mark.asyncio
async def test_hitung_semua_harga_ini_is_object_quantifier():
    """7. 'hitung semua harga ini' -> NOT all agents (Object Quantifier Mode C)."""
    msg = NormalizedMessage(message_id="m7", group_id="g1", sender_id="u1", text="hitung semua harga ini")
    res = await addressing_detector.detect(msg)
    assert res.addressing_type == AddressingType.NONE
    assert res.allow_multi_response is False


@pytest.mark.asyncio
async def test_cek_semua_produk_is_object_quantifier():
    """8. 'cek semua produk' -> NOT all agents."""
    msg = NormalizedMessage(message_id="m8", group_id="g1", sender_id="u1", text="cek semua produk")
    res = await addressing_detector.detect(msg)
    assert res.addressing_type == AddressingType.NONE


@pytest.mark.asyncio
async def test_baca_semua_file_ini_is_object_quantifier():
    """9. 'baca semua file ini' -> NOT all agents."""
    msg = NormalizedMessage(message_id="m9", group_id="g1", sender_id="u1", text="baca semua file ini")
    res = await addressing_detector.detect(msg)
    assert res.addressing_type == AddressingType.NONE


@pytest.mark.asyncio
async def test_hapus_semua_task_selesai_is_object_quantifier():
    """10. 'hapus semua task selesai' -> NOT all agents."""
    msg = NormalizedMessage(message_id="m10", group_id="g1", sender_id="u1", text="hapus semua task selesai")
    res = await addressing_detector.detect(msg)
    assert res.addressing_type == AddressingType.NONE


@pytest.mark.asyncio
async def test_semua_harga_ini_salah_is_object_quantifier():
    """11. 'semua harga ini salah' -> NOT all agents."""
    msg = NormalizedMessage(message_id="m11", group_id="g1", sender_id="u1", text="semua harga ini salah")
    res = await addressing_detector.detect(msg)
    assert res.addressing_type == AddressingType.NONE


@pytest.mark.asyncio
async def test_semua_bantu_strategi_launch_is_work_collaboration(orchestrator, mock_adapter):
    """12. 'semua, bantu strategi launch' -> all-agent work request via coordinator."""
    msg = NormalizedMessage(
        message_id="msg_work_all",
        group_id="group_core_team_01",
        sender_id="user_bima_01",
        text="semua, bantu strategi launch",
    )
    res = await addressing_detector.detect(msg)
    assert res.addressing_type == AddressingType.ALL_AGENTS
    assert res.intent == MessageIntent.WORK_REQUEST
    assert res.requires_coordinator is True
    assert res.coordinator == RoleID.MANAGER

    await orchestrator.handle_incoming_message(msg)
    # Manager koordinator mengirim pertama, lalu anggota lain menyumbang respon
    assert len(mock_adapter.sent_messages) >= 2


@pytest.mark.asyncio
async def test_manager_dan_advisor_evaluasi_keputusan_two_agents_work(orchestrator, mock_adapter):
    """13. 'Manager dan Advisor, evaluasi keputusan ini' -> only Manager + Advisor collaboration."""
    msg = NormalizedMessage(
        message_id="msg_work_two",
        group_id="group_core_team_01",
        sender_id="user_bima_01",
        text="Manager dan Advisor, evaluasi keputusan ini",
    )
    res = await addressing_detector.detect(msg)
    assert res.addressing_type == AddressingType.MULTIPLE_AGENTS
    assert set(res.target_agents) == {RoleID.MANAGER, RoleID.ADVISOR}
    assert res.intent == MessageIntent.WORK_REQUEST

    await orchestrator.handle_incoming_message(msg)
    roles_sent = {m["from_role"] for m in mock_adapter.sent_messages}
    assert "marketing" not in roles_sent


@pytest.mark.asyncio
async def test_semua_siap_is_social_response():
    """14. 'semua siap?' -> all-agent social response."""
    msg = NormalizedMessage(message_id="m14", group_id="g1", sender_id="u1", text="semua siap?")
    res = await addressing_detector.detect(msg)
    assert res.addressing_type == AddressingType.ALL_AGENTS
    assert res.intent == MessageIntent.SOCIAL


@pytest.mark.asyncio
async def test_semua_task_sudah_selesai_is_object_quantifier():
    """15. 'semua task sudah selesai?' -> object quantifier (not broadcast)."""
    msg = NormalizedMessage(message_id="m15", group_id="g1", sender_id="u1", text="semua task sudah selesai?")
    res = await addressing_detector.detect(msg)
    assert res.addressing_type == AddressingType.NONE


@pytest.mark.asyncio
async def test_social_broadcast_does_not_create_task_or_pollute_durable_memory(orchestrator, mock_adapter):
    """16. Social broadcast tidak membuat task baru dan tidak menulis ke durable memory."""
    init_tasks = await task_service.list_active_tasks("group_core_team_01")

    msg = NormalizedMessage(
        message_id="msg_social_safe",
        group_id="group_core_team_01",
        sender_id="user_bima_01",
        text="halo semua",
    )
    await orchestrator.handle_incoming_message(msg)

    final_tasks = await task_service.list_active_tasks("group_core_team_01")
    assert len(final_tasks) == len(init_tasks)  # Tidak ada task baru yang dibuat!


def test_social_responses_follow_each_agent_persona():
    responses = {
        role: social_response(role, "hai tim")
        for role in (RoleID.MANAGER, RoleID.MARKETING, RoleID.ADVISOR)
    }

    assert len(set(responses.values())) == 3
    assert "prioritas" in responses[RoleID.MANAGER]
    assert "Marketing" in responses[RoleID.MARKETING]
    assert "risiko" in responses[RoleID.ADVISOR]


def test_time_based_social_responses_keep_each_agent_persona():
    responses = {
        role: social_response(role, "pagi semua")
        for role in (RoleID.MANAGER, RoleID.MARKETING, RoleID.ADVISOR)
    }

    assert len(set(responses.values())) == 3
    assert "arah kerja" in responses[RoleID.MANAGER]
    assert "scroll" in responses[RoleID.MARKETING]
    assert "risiko" in responses[RoleID.ADVISOR]
