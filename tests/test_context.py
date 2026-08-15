"""Pengujian Kontrak Penerimaan AC-019: Context Assembly & No History Leak."""

import pytest

from src.agents.manager import manager_agent
from src.core.types import NormalizedMessage


@pytest.mark.asyncio
async def test_ac019_context_assembly_structure():
    """AC-019: Konteks agen dirakit secara selektif tanpa menyertakan riwayat obrolan mentah."""
    msg = NormalizedMessage(
        message_id="msg_ctx_01",
        group_id="group_core_team_01",
        sender_id="user_bima_01",
        text="Tolong buatkan rencana sprint minggu depan",
    )

    assembled = await manager_agent.assemble_context(msg)
    assert len(assembled) == 2
    system_prompt = assembled[0]["content"]
    user_prompt = assembled[1]["content"]

    assert "KEAHLIAN YANG TERSEDIA (SKILLS)" in system_prompt
    assert "MEMORI BERSAMA AKTIF" in system_prompt
    assert "TUGAS AKTIF SAYA" in system_prompt
    assert "Tolong buatkan rencana sprint minggu depan" in user_prompt
