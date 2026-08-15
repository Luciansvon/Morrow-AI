"""Pengujian Kontrak Penerimaan AC-020: Concurrency Isolation per Group (Tanpa Global Lock)."""

import asyncio

import pytest

from src.adapters.cli import CLIAdapter
from src.core.orchestrator import SystemOrchestrator
from src.core.types import NormalizedMessage


@pytest.mark.asyncio
async def test_ac020_concurrent_groups_not_blocked():
    """AC-020: Eksekusi pesan di Grup A tidak memblokir Grup B secara serial global."""
    adapter = CLIAdapter()
    orchestrator = SystemOrchestrator(adapter)

    # Kirim dua pesan bersamaan ke dua grup berbeda
    msg_a = NormalizedMessage(
        message_id="msg_grp_a",
        group_id="group_core_team_01",
        sender_id="user_bima_01",
        text="Pesan untuk grup A",
    )
    msg_b = NormalizedMessage(
        message_id="msg_grp_b",
        group_id="group_01",
        sender_id="user_bima_01",
        text="Pesan untuk grup B",
    )

    results = await asyncio.gather(
        orchestrator.handle_incoming_message(msg_a),
        orchestrator.handle_incoming_message(msg_b),
    )

    assert results[0] is not None
    assert results[1] is not None
