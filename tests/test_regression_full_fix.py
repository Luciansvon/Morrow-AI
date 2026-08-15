"""Regression tests for the full-fix branch."""

import asyncio
import io
from types import SimpleNamespace

import pytest
from PIL import Image

from src.adapters.base import BaseChannelAdapter
from src.approval.gateway import approval_gateway
from src.core.config import settings
from src.core.normalizer import MessageNormalizer
from src.core.orchestrator import SystemOrchestrator
from src.core.types import MemoryScope, NormalizedMessage, RoleID
from src.files.pipeline import attachment_pipeline
from src.llm.model_catalog import MODEL_CATALOG
from src.llm.openrouter import OpenRouterProvider
from src.memory.service import memory_service
from src.storage.sqlite import DatabaseManager
from src.tools.executor import tool_executor
from src.tools.registry import tool_registry


def test_database_manager_respects_database_path(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "sqlite_db_path", "")
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "expected.db"))
    manager = DatabaseManager()
    assert manager.db_path == str(tmp_path / "expected.db")


@pytest.mark.asyncio
async def test_atomic_dedup_concurrent_claim_has_single_winner():
    results = await asyncio.gather(*[
        MessageNormalizer.claim_event("42", "telegram", "-100999") for _ in range(12)
    ])
    assert sum(bool(x) for x in results) == 1


@pytest.mark.asyncio
async def test_dedup_scoped_by_group():
    assert await MessageNormalizer.claim_event("99", "telegram", "group-a") is True
    assert await MessageNormalizer.claim_event("99", "telegram", "group-b") is True


@pytest.mark.asyncio
async def test_memory_isolated_between_groups():
    await memory_service.set_memory(MemoryScope.SHARED, "deadline", "A", "u", group_id="g-a")
    await memory_service.set_memory(MemoryScope.SHARED, "deadline", "B", "u", group_id="g-b")
    assert (await memory_service.get_active_shared_memory("g-a"))["deadline"] == "A"
    assert (await memory_service.get_active_shared_memory("g-b"))["deadline"] == "B"


@pytest.mark.asyncio
async def test_missing_known_tool_never_reports_fake_success():
    result = await tool_executor.execute_tool("read_attachment", {"file_id": "x"})
    assert result["success"] is False
    assert result["error"] == "TOOL_NOT_REGISTERED"


@pytest.mark.asyncio
async def test_approval_executes_exact_tool_once():
    calls = {"count": 0}

    async def fake_send_email(to: str, subject: str):
        calls["count"] += 1
        return {"message_id": "m-1", "to": to, "subject": subject}

    tool_registry.register_tool("send_email", fake_send_email)
    req = await approval_gateway.create_request(
        "group_core_team_01",
        "send_email",
        {"to": "client@example.com", "subject": "Proposal"},
        RoleID.MANAGER,
    )
    ok, _ = await approval_gateway.approve_request(
        req.approval_id, "user_bima_01", expected_group_id="group_core_team_01"
    )
    assert ok is True
    first = await approval_gateway.execute_approved_request(req.approval_id)
    second = await approval_gateway.execute_approved_request(req.approval_id)
    assert first["success"] is True
    assert second["success"] is True
    assert calls["count"] == 1


@pytest.mark.asyncio
async def test_reasoning_effort_is_forwarded_to_openrouter():
    captured = {}

    class FakeCompletions:
        async def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="ok", tool_calls=None))],
                usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1, prompt_tokens_details=None, completion_tokens_details=None),
            )

    provider = OpenRouterProvider(api_key="real-looking-test-key")
    provider._client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    await provider._call_api(
        model="deepseek/deepseek-v4-flash",
        messages=[{"role": "user", "content": "x"}],
        temperature=0.1,
        response_format=None,
        tools=None,
        reasoning_effort="high",
    )
    assert captured["extra_body"]["reasoning"]["effort"] == "high"


def test_model_catalog_uses_current_stable_slugs():
    assert MODEL_CATALOG["deepseek_v4_flash"].model_id == "deepseek/deepseek-v4-flash"
    assert MODEL_CATALOG["deepseek_v4_pro"].model_id == "deepseek/deepseek-v4-pro"
    assert MODEL_CATALOG["gpt_5_6_luna"].model_id == "openai/gpt-5.6-luna"


@pytest.mark.asyncio
async def test_spoofed_pdf_is_rejected():
    att = await attachment_pipeline.process_bytes("invoice.pdf", b"MZ-this-is-not-a-pdf")
    assert att.is_supported is False
    assert "tidak konsisten" in (att.error_message or "")


@pytest.mark.asyncio
async def test_mock_image_pipeline_produces_visual_context():
    buf = io.BytesIO()
    Image.new("RGB", (32, 24), "white").save(buf, format="PNG")
    att = await attachment_pipeline.process_bytes("poster.png", buf.getvalue())
    assert att.is_supported is True
    assert att.visual_description


class CaptureAdapter(BaseChannelAdapter):
    def __init__(self):
        super().__init__()
        self.sent = []

    async def start(self):
        pass

    async def stop(self):
        pass

    async def send_message(self, group_id, text, from_role=None, reply_to_message_id=None):
        msg_id = f"out-{len(self.sent)+1}"
        self.sent.append((from_role, text, msg_id))
        return msg_id

    async def send_approval_prompt(self, group_id, approval_id, action_description, parameters):
        pass


@pytest.mark.asyncio
async def test_halo_semua_is_zero_token_social_broadcast(monkeypatch):
    adapter = CaptureAdapter()
    orchestrator = SystemOrchestrator(adapter)

    async def explode(*args, **kwargs):
        raise AssertionError("LLM must not be called for deterministic social broadcast")

    for agent in orchestrator._agents.values():
        monkeypatch.setattr(agent, "execute", explode)
    result = await orchestrator.handle_incoming_message(NormalizedMessage(
        message_id="social-zero-token",
        group_id="group_core_team_01",
        sender_id="user_bima_01",
        text="halo semua",
    ))
    assert result is not None
    assert len(adapter.sent) == 3
    assert {role for role, _, _ in adapter.sent} == {RoleID.MANAGER, RoleID.MARKETING, RoleID.ADVISOR}
