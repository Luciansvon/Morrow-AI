"""Pengujian Kontrak Penerimaan AC-010 & AC-012: Memory Scope Isolation & Audit History."""

import pytest

from src.core.types import MemoryScope, RoleID
from src.memory.service import memory_service


@pytest.mark.asyncio
async def test_ac010_memory_audit_history_preserves_past_values():
    """AC-010: Perubahan keputusan menyimpan jejak riwayat masa lalu (old_value -> new_value)."""
    key = "deadline_peluncuran"

    await memory_service.set_memory(
        scope=MemoryScope.SHARED,
        key=key,
        value="2026-09-01",
        changed_by_actor="user_bima_01",
        reason="Jadwal awal peluncuran",
    )
    await memory_service.set_memory(
        scope=MemoryScope.SHARED,
        key=key,
        value="2026-09-15",
        changed_by_actor="user_bima_01",
        reason="Penyesuaian timeline kampanye",
    )

    audit_rows = await memory_service.get_memory_audit_history(key)
    assert len(audit_rows) == 2
    assert audit_rows[0]["old_value"] is None
    assert audit_rows[0]["new_value"] == "2026-09-01"
    assert audit_rows[1]["old_value"] == "2026-09-01"
    assert audit_rows[1]["new_value"] == "2026-09-15"


@pytest.mark.asyncio
async def test_ac012_role_memory_isolation():
    """AC-012: Memori peran Marketing terisolasi dari memori peran Advisor."""
    await memory_service.set_memory(
        scope=MemoryScope.ROLE,
        role_id=RoleID.MARKETING,
        key="target_cpa",
        value="Rp 50.000",
        changed_by_actor="marketing",
    )
    await memory_service.set_memory(
        scope=MemoryScope.ROLE,
        role_id=RoleID.ADVISOR,
        key="max_risk_tolerance",
        value="Tinggi",
        changed_by_actor="advisor",
    )

    mkt_mem = await memory_service.get_role_memory(RoleID.MARKETING)
    adv_mem = await memory_service.get_role_memory(RoleID.ADVISOR)
    assert "target_cpa" in mkt_mem
    assert "max_risk_tolerance" not in mkt_mem
    assert "max_risk_tolerance" in adv_mem
    assert "target_cpa" not in adv_mem


@pytest.mark.asyncio
async def test_shared_memory_rejects_role_id():
    """Shared memory tidak boleh membawa role_id yang membuat scope menjadi ambigu."""
    with pytest.raises(ValueError, match="shared memory"):
        await memory_service.set_memory(
            scope=MemoryScope.SHARED,
            role_id=RoleID.MARKETING,
            key="launch_date",
            value="2026-09-20",
            changed_by_actor="user_bima_01",
        )

    shared = await memory_service.get_active_shared_memory()
    assert "launch_date" not in shared
