"""Approval safety regression tests."""

import pytest

from src.approval.gateway import approval_gateway
from src.core.types import RoleID
from src.tools.executor import tool_executor


@pytest.mark.asyncio
async def test_external_action_requires_user_approval():
    """Aksi luar ditolak jika belum mendapat izin user."""
    res = await tool_executor.execute_tool(
        tool_name="send_email",
        parameters={"to": "client@example.com", "subject": "Proposal"},
        is_approved=False,
    )
    assert res["success"] is False
    assert res["requires_approval"] is True


@pytest.mark.asyncio
async def test_parameter_mutation_invalidates_approval():
    """Perubahan parameter setelah request dibuat membatalkan izin lama."""
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
