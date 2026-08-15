"""Regression coverage for hybrid low-RAM long-term memory."""

from pathlib import Path

import pytest

from src.core.config import settings
from src.core.types import MemoryScope, MemoryType, RoleID
from src.memory.service import memory_service
from src.storage.sqlite import db


@pytest.mark.asyncio
async def test_fts_tracks_updates_without_stale_content():
    await memory_service.set_memory(
        scope=MemoryScope.SHARED,
        key="buah_favorit",
        value="apel merah",
        changed_by_actor="u1",
        group_id="g1",
    )
    before = await db.fetch_all(
        "SELECT memory_id FROM memory_fts WHERE memory_fts MATCH ? AND group_id=?",
        ('"apel"', "g1"),
    )
    assert len(before) == 1

    await memory_service.set_memory(
        scope=MemoryScope.SHARED,
        key="buah_favorit",
        value="jeruk manis",
        changed_by_actor="u1",
        group_id="g1",
    )
    stale = await db.fetch_all(
        "SELECT memory_id FROM memory_fts WHERE memory_fts MATCH ? AND group_id=?",
        ('"apel"', "g1"),
    )
    current = await db.fetch_all(
        "SELECT memory_id FROM memory_fts WHERE memory_fts MATCH ? AND group_id=?",
        ('"jeruk"', "g1"),
    )
    assert stale == []
    assert len(current) == 1


@pytest.mark.asyncio
async def test_hybrid_retrieval_respects_role_scope():
    await memory_service.set_memory(
        scope=MemoryScope.SHARED,
        key="external_action_approval",
        value="email keluar wajib approval eksplisit",
        changed_by_actor="u1",
        memory_type=MemoryType.CONSTRAINT,
        group_id="g1",
    )
    await memory_service.set_memory(
        scope=MemoryScope.ROLE,
        role_id=RoleID.MARKETING,
        key="campaign_secret",
        value="campaign neon khusus marketing",
        changed_by_actor="u1",
        group_id="g1",
    )

    marketing = await memory_service.retrieve_relevant_memory(
        "approval email dan campaign neon",
        RoleID.MARKETING,
        "g1",
    )
    advisor = await memory_service.retrieve_relevant_memory(
        "campaign neon",
        RoleID.ADVISOR,
        "g1",
    )

    assert {row["key"] for row in marketing} >= {
        "external_action_approval",
        "campaign_secret",
    }
    assert "campaign_secret" not in {row["key"] for row in advisor}


@pytest.mark.asyncio
async def test_sqlite_vec_is_loaded_and_indexes_memory():
    assert db.vector_extension_loaded is True
    item = await memory_service.set_memory(
        scope=MemoryScope.SHARED,
        key="email_guardrail",
        value="email eksternal membutuhkan approval pengguna",
        changed_by_actor="u1",
        group_id="g1",
    )
    mapping = await db.fetch_one(
        "SELECT memory_id, dimensions FROM memory_vector_map WHERE memory_id=?",
        (item.id,),
    )
    assert mapping is not None
    assert mapping["memory_id"] == item.id
    assert int(mapping["dimensions"]) == settings.memory_embedding_dimensions

    hits = await memory_service.retrieve_relevant_memory(
        "approval email eksternal",
        RoleID.MANAGER,
        "g1",
    )
    assert hits
    assert hits[0]["key"] == "email_guardrail"


@pytest.mark.asyncio
async def test_markdown_vault_is_managed_mirror():
    await memory_service.set_memory(
        scope=MemoryScope.ROLE,
        role_id=RoleID.ADVISOR,
        key="risk_rule",
        value="hindari keputusan irreversible tanpa review",
        changed_by_actor="u1",
        memory_type=MemoryType.CONSTRAINT,
        group_id="g1",
    )

    path = Path(settings.memory_vault_dir) / "g1" / "roles" / "advisor.md"
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "MORROW-MANAGED MIRROR" in content
    assert "risk_rule" in content
    assert "irreversible" in content
