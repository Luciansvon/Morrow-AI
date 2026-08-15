"""Pengujian Kontrak Penerimaan AC-002, AC-003, AC-004: Routing & Reply-Aware Mapping."""

import pytest

from src.core.types import NormalizedMessage, RoleID
from src.routing.fast_path import fast_path_router
from src.routing.role_router import role_router
from src.storage.sqlite import db


@pytest.mark.asyncio
async def test_ac002_fast_path_explicit_mention():
    """AC-002: Pesan yang menyebut nama/peran secara eksplisit disalurkan langsung via Fast Path."""
    msg = NormalizedMessage(
        message_id="msg_fp_01",
        group_id="group_core_team_01",
        sender_id="user_bima_01",
        text="@marketing tolong buatkan ide kampanye produk",
    )
    result = await fast_path_router.resolve_fast_path(msg)
    assert result is not None
    role, reason = result
    assert role == RoleID.MARKETING
    assert "Sebutan eksplisit" in reason


@pytest.mark.asyncio
async def test_ac003_semantic_router_single_primary_agent():
    """AC-003: Pesan ambigu disalurkan ke TEPAT SATU agen utama."""
    msg = NormalizedMessage(
        message_id="msg_sr_01",
        group_id="group_core_team_01",
        sender_id="user_bima_01",
        text="Tolong bantu atur jadwal meeting mingguan dan delegasikan tugas",
    )
    primary_role, reason = await role_router.route_message(msg)
    assert primary_role in (RoleID.MANAGER, RoleID.MARKETING, RoleID.ADVISOR)
    assert isinstance(primary_role, RoleID)


@pytest.mark.asyncio
async def test_ac004_reply_aware_routing():
    """AC-004: Membalas pesan yang dihasilkan agen sebelumnya diteruskan ke agen pembuat awal."""
    # 1. Simpan pesan yang sebelumnya dibuat oleh Advisor
    original_msg_id = "adv_reply_test_123"
    await db.execute(
        """
        INSERT INTO message_agent_map (platform_message_id, originating_role_id, group_id)
        VALUES (?, ?, ?)
        """,
        (original_msg_id, "advisor", "group_core_team_01"),
    )

    # 2. Pengguna membalas pesan tersebut tanpa menyebutkan nama agen
    reply_msg = NormalizedMessage(
        message_id="user_msg_reply_01",
        group_id="group_core_team_01",
        sender_id="user_bima_01",
        text="Saya setuju dengan opsi nomor dua, tolong jelaskan detailnya",
        reply_to_message_id=original_msg_id,
    )

    result = await fast_path_router.resolve_fast_path(reply_msg)
    assert result is not None
    role, reason = result
    assert role == RoleID.ADVISOR
    assert "Reply-Aware Mapping" in reason
