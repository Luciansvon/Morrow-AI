"""Pengujian Kontrak Penerimaan AC-013 & AC-022: External Approval & Parameter Hash Mutation."""

import pytest

from src.approval.gateway import approval_gateway
from src.core.types import RoleID
from src.tools.executor import tool_executor


@pytest.mark.asyncio
async def test_ac013_external_action_requires_user_approval():
    """AC-013: Aksi luar (kirim email) ditolak dieksekusi langsung tanpa izin user."""
    res = await tool_executor.execute_tool(
        tool_name="send_email",
        parameters={"to": "client@example.com", "subject": "Proposal"},
        is_approved=False,
    )
    assert res["success"] is False
    assert res["requires_approval"] is True


@pytest.mark.asyncio
async def test_ac022_parameter_mutation_invalidates_approval():
    """AC-022: Perubahan isi parameter setelah approval diajukan membatalkan izin (Parameter Mutation Protection)."""
    initial_params = {"to": "client@example.com", "amount": 1000}
    req = await approval_gateway.create_request(
        group_id="group_core_team_01",
        action_type="execute_transaction",
        parameters=initial_params,
        requested_by=RoleID.MANAGER,
    )

    # Pengguna mencoba menyetujui, tetapi parameter disusupi perubahan nilai (amount: 50000)
    mutated_params = {"to": "client@example.com", "amount": 50000}
    is_ok, reason = await approval_gateway.approve_request(
        approval_id=req.approval_id,
        approved_by="user_bima_01",
        current_parameters=mutated_params,
    )
    assert is_ok is False
    assert "Parameter aksi telah berubah" in reason
