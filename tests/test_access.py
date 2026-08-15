"""Pengujian Kontrak Penerimaan AC-001: Access Control (Whitelist & Allowlist)."""

import pytest

from src.core.normalizer import MessageNormalizer
from src.core.types import NormalizedMessage


@pytest.mark.asyncio
async def test_whitelisted_user_in_allowlisted_group_allowed():
    """Pengguna terdaftar di grup terdaftar harus diizinkan."""
    msg = NormalizedMessage(
        message_id="msg_001",
        group_id="group_core_team_01",
        sender_id="user_bima_01",
        text="Halo tim",
    )
    is_allowed, reason = MessageNormalizer.check_access(msg)
    assert is_allowed is True
    assert reason is None


@pytest.mark.asyncio
async def test_non_whitelisted_user_rejected():
    """Pengguna tidak terdaftar dalam whitelist harus ditolak."""
    msg = NormalizedMessage(
        message_id="msg_002",
        group_id="group_core_team_01",
        sender_id="unknown_user_99",
        text="Halo saya penyusup",
    )
    is_allowed, reason = MessageNormalizer.check_access(msg)
    assert is_allowed is False
    assert "tidak terdaftar dalam whitelist" in reason


@pytest.mark.asyncio
async def test_non_allowlisted_group_rejected():
    """Grup tidak terdaftar dalam allowlist harus ditolak."""
    msg = NormalizedMessage(
        message_id="msg_003",
        group_id="unregistered_random_group",
        sender_id="user_bima_01",
        text="Halo di grup luar",
    )
    is_allowed, reason = MessageNormalizer.check_access(msg)
    assert is_allowed is False
    assert "tidak terdaftar dalam group allowlist" in reason
