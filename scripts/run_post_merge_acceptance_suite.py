"""Post-merge acceptance suite for Morrow dispatch, browser, persona, and memory contracts.

Unlike the older harness, PASS is evidence-backed: browser COMMIT goes through ApprovalGateway,
and multi-agent completion is verified from the durable task_agent_runs ledger.
"""

import asyncio
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.adapters.base import BaseChannelAdapter
from src.approval.gateway import approval_gateway
from src.browser.base import BrowserActionClass, BrowserBackendUnavailableError
from src.browser.provider import (
    browser_backend_availability,
    get_browser_backend,
    validate_browser_runtime,
)
from src.browser.tools import ensure_browser_tools_registered
from src.core.config import settings
from src.core.orchestrator import SystemOrchestrator
from src.core.types import NormalizedMessage, RoleID
from src.memory.service import memory_service
from src.storage.sqlite import db
from src.tasks.service import task_service
from src.tools.builtins import ensure_builtin_tools_registered


class LiveTrackingAdapter(BaseChannelAdapter):
    def __init__(self):
        super().__init__()
        self.sent_messages: list[dict[str, Any]] = []
        self.activities: list[dict[str, Any]] = []

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    async def send_message(self, group_id, text, from_role=None, reply_to_message_id=None):
        msg_id = f"live_msg_{len(self.sent_messages) + 1}_{int(time.time() * 1000)}"
        self.sent_messages.append({
            "id": msg_id,
            "group_id": group_id,
            "text": text,
            "from_role": from_role.value if isinstance(from_role, RoleID) else str(from_role),
            "reply_to": reply_to_message_id,
        })
        return msg_id

    async def send_approval_prompt(self, group_id, approval_id, action_description, parameters):
        self.sent_messages.append({
            "id": f"approval_{approval_id}",
            "group_id": group_id,
            "text": action_description,
            "from_role": "system",
            "reply_to": None,
        })

    async def begin_activity(self, group_id, text, from_role, reply_to_message_id=None):
        activity_id = f"activity_{len(self.activities) + 1}"
        self.activities.append({"id": activity_id, "status": "active", "role": from_role.value})
        return activity_id

    async def end_activity(self, group_id, activity_id, from_role):
        for activity in self.activities:
            if activity["id"] == activity_id:
                activity["status"] = "ended"


async def run_suite() -> list[dict[str, Any]]:
    print("=" * 76)
    print("MORROW POST-MERGE ACCEPTANCE — EVIDENCE-BACKED")
    print("=" * 76)

    settings.browser_enabled = True
    settings.browser_backend = "agent-browser"
    settings.browser_agent_executable = "agent-browser"
    await db.init_schema()
    ensure_builtin_tools_registered()
    ensure_browser_tools_registered()
    await memory_service.initialize_long_term_memory()

    adapter = LiveTrackingAdapter()
    orchestrator = SystemOrchestrator(adapter)
    group_id = "-1003705099535"
    sender_id = "5497600429"
    results: list[dict[str, Any]] = []

    def record(test_id: str, title: str, passed: bool, reason: str, evidence: dict[str, Any] | None = None):
        result = "PASS" if passed else "FAIL"
        row = {"id": test_id, "title": title, "result": result, "reason": reason, "evidence": evidence or {}}
        results.append(row)
        print(f"[{test_id}] {result}: {title} — {reason}")

    async def ask(message_id: str, text: str) -> str:
        before = len(adapter.sent_messages)
        result = await orchestrator.handle_incoming_message(
            NormalizedMessage(
                platform="telegram",
                group_id=group_id,
                sender_id=sender_id,
                sender_name="Bima",
                text=text,
                timestamp=datetime.now(UTC),
                message_id=message_id,
            )
        )
        if result is not None:
            return result
        return adapter.sent_messages[-1]["text"] if len(adapter.sent_messages) > before else ""

    available, detail = browser_backend_availability()
    negative_ok = False
    original_executable = settings.browser_agent_executable
    try:
        settings.browser_agent_executable = "missing-agent-browser-test"
        try:
            validate_browser_runtime()
        except BrowserBackendUnavailableError:
            negative_ok = True
    finally:
        settings.browser_agent_executable = original_executable
    record("PHASE-2", "Browser startup preflight", available and negative_ok, "provider tersedia dan invalid executable fail-closed" if available and negative_ok else f"available={available}, negative={negative_ok}", {"detail": detail})

    backend = get_browser_backend()
    demo_url = "https://www.selenium.dev/selenium/web/web-form.html"

    read_space = f"accept-read-{int(time.time())}"
    try:
        opened = await backend.open("https://example.com", task_space=read_space)
        snapshot = await backend.snapshot(task_space=read_space)
        read_ok = bool(opened.get("success")) and bool(snapshot.get("success"))
        record("PHASE-3", "Browser READ", read_ok, "open + snapshot sukses" if read_ok else "open/snapshot gagal", {"open": opened, "snapshot": snapshot})
    except Exception as exc:
        record("PHASE-3", "Browser READ", False, f"{exc.__class__.__name__}: {exc}")

    prepare_space = f"accept-prepare-{int(time.time())}"
    try:
        await backend.open(demo_url, task_space=prepare_space)
        prepared = await backend.interact(
            "fill",
            {"target": "#my-text-id", "value": "Morrow Prepare Test"},
            task_space=prepare_space,
            action_class=BrowserActionClass.PREPARE,
        )
        record("PHASE-4", "Browser PREPARE", bool(prepared.get("success")), "fill lokal sukses tanpa COMMIT", {"result": prepared})
    except Exception as exc:
        record("PHASE-4", "Browser PREPARE", False, f"{exc.__class__.__name__}: {exc}")

    commit_space = f"accept-commit-{int(time.time())}"
    try:
        await backend.open(demo_url, task_space=commit_space)
        await backend.interact(
            "fill",
            {"target": "#my-text-id", "value": "Approval Flow Test"},
            task_space=commit_space,
            action_class=BrowserActionClass.PREPARE,
        )
        request = await approval_gateway.create_request(
            group_id,
            "browser_click",
            {"target": "button[type='submit']", "_task_space": commit_space},
            RoleID.MANAGER,
        )
        approved, _ = await approval_gateway.approve_request(request.approval_id, sender_id, expected_group_id=group_id)
        execution = await approval_gateway.execute_approved_request(request.approval_id) if approved else {"success": False}
        record("PHASE-5", "Approval-gated browser COMMIT", approved and bool(execution.get("success")), "COMMIT dieksekusi via ApprovalGateway" if approved and execution.get("success") else "approval/execution gagal", {"approval_id": request.approval_id, "execution": execution})
    except Exception as exc:
        record("PHASE-5", "Approval-gated browser COMMIT", False, f"{exc.__class__.__name__}: {exc}")

    stale_space = f"accept-stale-{int(time.time())}"
    try:
        await backend.open(demo_url, task_space=stale_space)
        await backend.interact("fill", {"target": "#my-text-id", "value": "Alice"}, task_space=stale_space, action_class=BrowserActionClass.PREPARE)
        stale_req = await approval_gateway.create_request(group_id, "browser_click", {"target": "button[type='submit']", "_task_space": stale_space}, RoleID.MANAGER)
        await backend.interact("fill", {"target": "#my-text-id", "value": "Bob"}, task_space=stale_space, action_class=BrowserActionClass.PREPARE)
        stale_approved, _ = await approval_gateway.approve_request(stale_req.approval_id, sender_id, expected_group_id=group_id)
        stale_exec = await approval_gateway.execute_approved_request(stale_req.approval_id) if stale_approved else {"success": False}
        fresh_req = await approval_gateway.create_request(group_id, "browser_click", {"target": "button[type='submit']", "_task_space": stale_space}, RoleID.MANAGER)
        fresh_approved, _ = await approval_gateway.approve_request(fresh_req.approval_id, sender_id, expected_group_id=group_id)
        fresh_exec = await approval_gateway.execute_approved_request(fresh_req.approval_id) if fresh_approved else {"success": False}
        stale_rejected = not stale_exec.get("success") and "BROWSER_STATE_CHANGED" in str(stale_exec.get("error"))
        record("PHASE-6", "Changed-state approval invalidation", stale_rejected and bool(fresh_exec.get("success")), "stale ditolak dan approval fresh berhasil", {"stale": stale_exec, "fresh": fresh_exec})
    except Exception as exc:
        record("PHASE-6", "Changed-state approval invalidation", False, f"{exc.__class__.__name__}: {exc}")

    marketing = await ask("accept-persona-mkt", "Marketing, penjualan handmade wood stagnan. Apa yang harus dilakukan?")
    manager = await ask("accept-persona-mgr", "Manager, terlalu banyak ide dan semuanya dianggap penting. Apa yang kita lakukan?")
    advisor = await ask("accept-persona-adv", "Advisor, kita kepikiran mengorbankan trust user supaya growth lebih cepat. Gimana menurut kamu?")
    mkt_ok = sum(k in marketing.lower() for k in ["audience", "audiens", "hipotesis", "eksperimen", "metric", "metrik", "data", "pasar"]) >= 2
    mgr_ok = sum(k in manager.lower() for k in ["prioritas", "fokus", "keputusan", "langkah", "eksekusi", "owner"]) >= 2
    adv_ok = sum(k in advisor.lower() for k in ["risiko", "trust", "kepercayaan", "reputasi", "jangka panjang", "trade-off"]) >= 2
    record("PHASE-8", "Persona role behavior", mkt_ok and mgr_ok and adv_ok, "ketiga role menunjukkan domain perilaku berbeda", {"marketing": marketing[:200], "manager": manager[:200], "advisor": advisor[:200]})
    record("PHASE-9", "Cross-persona differentiation", len({marketing, manager, advisor}) == 3, "respons tidak identik antar-role")

    serious = await ask("accept-serious", "Marketing, kita punya risiko kehilangan data user dan reputasi. Analisis situasinya.")
    no_humor = not any(x in serious.lower() for x in ["haha", "wkwk", "lol", "🤣", "😂"])
    record("PHASE-10", "Serious-context humor suppression", no_humor, "humor tersupresi pada konteks risiko" if no_humor else "humor masih muncul")

    multi_prompt = "Advisor dan Manager, tentukan apakah integrasi email layak diprioritaskan minggu ini."
    multi = await ask("accept-multi", multi_prompt)
    task = await db.fetch_one(
        "SELECT id, status FROM tasks WHERE group_id=? AND title=? ORDER BY created_at DESC LIMIT 1",
        (group_id, multi_prompt[:120]),
    )
    runs = await task_service.list_agent_runs(task["id"]) if task else []
    succeeded = {row["role_id"] for row in runs if row["status"] == "succeeded"}
    exact_roles = succeeded == {"advisor", "manager"}
    task_done = bool(task and task["status"] == "done")
    record("PHASE-11", "Multi-agent authority and completion", exact_roles and task_done, "Advisor + Manager terverifikasi di ledger dan task done" if exact_roles and task_done else "ledger tidak memenuhi kontrak multi-agent", {"response": multi[:200], "task": task, "runs": runs})

    commit_ack = await ask("accept-memory-write", "Manager, catat sebagai keputusan: browser production Morrow menggunakan agent-browser.")
    recall = await ask("accept-memory-read", "Advisor, apa keputusan kita soal browser production?")
    memory_ok = commit_ack.startswith("Sudah dicatat ke memori bersama") and "browser" in recall.lower()
    record("PHASE-12", "Memory commit and cross-role recall", memory_ok, "write backend terverifikasi dan recall memuat keputusan browser" if memory_ok else "write/recall tidak lengkap", {"ack": commit_ack, "recall": recall})

    await ask("accept-activity", "Manager, sebutkan ringkas status kesiapan tim kita.")
    activities_ok = all(activity["status"] == "ended" for activity in adapter.activities)
    record("PHASE-13", "Activity lifecycle", activities_ok, "semua activity preview ditutup" if activities_ok else "ada activity yang tertinggal", {"activities": adapter.activities})

    out = REPO_ROOT / "scripts" / "post_merge_acceptance_results.json"
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print("=" * 76)
    print(f"Saved: {out}")
    failures = [row for row in results if row["result"] == "FAIL"]
    if failures:
        raise SystemExit(f"Acceptance gagal: {len(failures)} phase")
    return results


if __name__ == "__main__":
    asyncio.run(run_suite())
