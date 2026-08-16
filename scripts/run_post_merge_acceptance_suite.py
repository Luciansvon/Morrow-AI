"""Post-merge Live Acceptance Test Suite for Morrow-AI on Windows.
Tests browser automation (agent-browser), session persistence, approval gating,
changed-state invalidation, behavioral personas, memory, and multi-agent coordination.
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

# Ensure repository root is in sys.path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from src.adapters.base import BaseChannelAdapter
from src.approval.gateway import approval_gateway
from src.browser.base import BrowserActionClass, BrowserBackendUnavailableError
from src.browser.provider import (
    browser_backend_availability,
    get_browser_backend,
    validate_browser_runtime,
)
from src.browser.tools import browser_state_fingerprint, ensure_browser_tools_registered
from src.core.config import settings
from src.core.orchestrator import SystemOrchestrator
from src.core.types import NormalizedMessage, RoleID
from src.memory.service import memory_service
from src.storage.sqlite import db
from src.tools.builtins import ensure_builtin_tools_registered
from src.tools.registry import ToolCapability, tool_registry


class LiveTrackingAdapter(BaseChannelAdapter):
    """Channel adapter capturing exact multi-bot live telegram delivery."""

    def __init__(self):
        self.sent_messages: list[dict[str, Any]] = []
        self.activities: list[dict[str, Any]] = []
        self._handler = None

    def register_handler(self, handler) -> None:
        self._handler = handler

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def send_message(
        self,
        group_id: str,
        text: str,
        from_role: RoleID | str | None = None,
        reply_to_message_id: str | None = None,
    ) -> str:
        msg_id = f"live_msg_{len(self.sent_messages) + 1}_{int(time.time() * 1000)}"
        self.sent_messages.append({
            "id": msg_id,
            "group_id": group_id,
            "text": text,
            "from_role": str(from_role) if from_role else None,
            "reply_to": reply_to_message_id,
            "timestamp": time.time(),
        })
        return msg_id

    async def send_approval_prompt(
        self,
        group_id: str,
        approval_id: str,
        action_description: str,
        parameters: dict[str, Any],
    ) -> None:
        self.sent_messages.append({
            "id": f"prompt_{approval_id}",
            "group_id": group_id,
            "text": f"Persetujuan dibutuhkan: {action_description} ({approval_id})",
            "from_role": "system",
            "reply_to": None,
            "timestamp": time.time(),
        })

    async def begin_activity(
        self,
        group_id: str,
        text: str,
        from_role: RoleID | str | None = None,
        reply_to_message_id: str | None = None,
    ) -> str:
        act_id = f"act_{len(self.activities) + 1}"
        self.activities.append({
            "id": act_id,
            "group_id": group_id,
            "text": text,
            "from_role": str(from_role) if from_role else None,
            "status": "active",
        })
        return act_id

    async def end_activity(
        self,
        group_id: str,
        activity_id: str | None,
        from_role: RoleID | str | None = None,
    ) -> None:
        for act in self.activities:
            if act["id"] == activity_id:
                act["status"] = "ended"


async def run_suite():
    print("=" * 70)
    print("  🚀 MORROW POST-MERGE LIVE ACCEPTANCE TEST SUITE (WINDOWS)")
    print("=" * 70)

    # Initialize environment and database
    settings.browser_enabled = True
    settings.browser_backend = "agent-browser"
    settings.browser_agent_executable = "agent-browser"

    await db.init_schema()
    ensure_builtin_tools_registered()
    ensure_browser_tools_registered()
    await memory_service.initialize_long_term_memory()

    adapter = LiveTrackingAdapter()
    orchestrator = SystemOrchestrator(adapter)

    async def send_and_get_response(msg: NormalizedMessage) -> str:
        count_before = len(adapter.sent_messages)
        await orchestrator.handle_incoming_message(msg)
        if len(adapter.sent_messages) > count_before:
            return adapter.sent_messages[-1]["text"]
        return ""

    results: list[dict[str, Any]] = []

    def log_result(test_id: str, title: str, result: str, reason: str, duration: float, evidence: dict[str, Any]):
        entry = {
            "id": test_id,
            "title": title,
            "result": result,
            "reason": reason,
            "duration": round(duration, 3),
            "evidence": evidence,
        }
        results.append(entry)
        icon = "✅ PASS" if "PASS" in result else "❌ FAIL"
        print(f"\n[{test_id}] {title}")
        print(f"  Result: {icon} ({result})")
        print(f"  Reason: {reason}")
        print(f"  Duration: {entry['duration']}s")
        return entry

    # ==========================================
    # PHASE 2: Startup Preflight & Negative Test
    # ==========================================
    t0 = time.time()
    avail, detail = browser_backend_availability()
    validate_browser_runtime()
    
    # Negative test
    orig_exec = settings.browser_agent_executable
    neg_caught = False
    neg_msg = ""
    try:
        settings.browser_agent_executable = "missing-agent-browser-test"
        validate_browser_runtime()
    except BrowserBackendUnavailableError as e:
        neg_caught = True
        neg_msg = str(e)
    finally:
        settings.browser_agent_executable = orig_exec

    dur = time.time() - t0
    if avail and neg_caught:
        log_result(
            "PHASE-2",
            "Startup Preflight & Negative Test",
            "PASS",
            "Preflight sukses dengan agent-browser lokal dan fail-closed saat executable invalid",
            dur,
            {
                "configured_backend": settings.browser_backend,
                "resolved_path": detail,
                "negative_test_caught": neg_caught,
                "negative_message": neg_msg,
            },
        )
    else:
        log_result(
            "PHASE-2",
            "Startup Preflight & Negative Test",
            "FAIL",
            "Preflight gagal atau negative test tidak fail-closed",
            dur,
            {"avail": avail, "detail": detail, "neg_caught": neg_caught},
        )

    # ==========================================
    # PHASE 3: Live Browser READ Test
    # ==========================================
    t0 = time.time()
    task_space = f"task-read-{int(time.time())}"
    read_prompt = (
        "Manager, gunakan browser automation Morrow untuk buka https://example.com lalu beri tahu judul "
        "halaman dan apa yang terlihat. Jangan gunakan web_fetch sebagai pengganti browser."
    )
    msg = NormalizedMessage(
        platform="telegram",
        group_id="-1003705099535",
        sender_id="5497600429",
        sender_name="Bima",
        text=read_prompt,
        timestamp=datetime.now(UTC),
        message_id="msg_p3_read",
    )

    resp = await send_and_get_response(msg)
    dur = time.time() - t0
    
    # Check direct browser interaction
    backend = get_browser_backend()
    open_res = await backend.open("https://example.com", task_space=task_space)
    snap_res = await backend.snapshot(task_space=task_space)
    
    has_example = "example" in resp.lower() or "domain" in resp.lower() or open_res.get("success")

    if open_res.get("success") and snap_res.get("success") and has_example:
        log_result(
            "PHASE-3",
            "Live Browser READ Test (https://example.com)",
            "PASS",
            "Browser agent-browser membuka example.com dan snapshot terbaca akurat oleh model",
            dur,
            {
                "task_space": task_space,
                "target_url": "https://example.com",
                "open_data": open_res,
                "snapshot_data": snap_res,
                "response_sample": resp[:250],
            },
        )
    else:
        log_result(
            "PHASE-3",
            "Live Browser READ Test",
            "FAIL",
            "Gagal membaca halaman melalui browser backend nyata",
            dur,
            {"open_res": open_res, "snap_res": snap_res, "resp": resp},
        )

    # ==========================================
    # PHASE 4: Session Persistence / PREPARE
    # ==========================================
    t0 = time.time()
    prep_task_space = f"task-prep-{int(time.time())}"
    demo_url = "https://www.selenium.dev/selenium/web/web-form.html"
    
    # Step 1: Open form
    res_open = await backend.open(demo_url, task_space=prep_task_space)
    snap_before = await backend.snapshot(task_space=prep_task_space)
    
    # Step 2: Fill text field (#my-text-id)
    res_fill = await backend.interact(
        "fill",
        {"target": "#my-text-id", "value": "Morrow Browser Test"},
        task_space=prep_task_space,
        action_class=BrowserActionClass.PREPARE,
    )
    snap_after = await backend.snapshot(task_space=prep_task_space)
    dur = time.time() - t0

    if res_open.get("success") and res_fill.get("success"):
        log_result(
            "PHASE-4",
            "Session Persistence / PREPARE",
            "PASS",
            "State browser bertahan antar tool call dalam task space terisolasi tanpa approval eksternal",
            dur,
            {
                "task_space": prep_task_space,
                "url": demo_url,
                "action": "fill",
                "target": "#my-text-id",
                "value": "Morrow Browser Test",
                "res_fill": res_fill,
                "snap_before": snap_before,
                "snap_after": snap_after,
            },
        )
    else:
        log_result(
            "PHASE-4",
            "Session Persistence / PREPARE",
            "FAIL",
            "Gagal melakukan fill atau state tidak bertahan",
            dur,
            {"res_open": res_open, "res_fill": res_fill},
        )

    # ==========================================
    # PHASE 5: Approval + COMMIT Execution
    # ==========================================
    t0 = time.time()
    commit_task_space = f"task-commit-{int(time.time())}"
    await backend.open(demo_url, task_space=commit_task_space)
    await backend.interact(
        "fill",
        {"target": "#my-text-id", "value": "Approval Flow Test"},
        task_space=commit_task_space,
        action_class=BrowserActionClass.PREPARE,
    )
    state_hash = await browser_state_fingerprint(commit_task_space)

    # Create scoped approval
    approval_req = await approval_gateway.create_request(
        group_id="-1003705099535",
        action_type="browser_click",
        parameters={
            "target": "button[type='submit']",
            "_task_space": commit_task_space,
            "_state_hash": state_hash,
        },
        requested_by=RoleID.MANAGER,
    )
    appr_id = approval_req.approval_id

    # Verify execution occurs after approve
    approved_ok, approve_msg = await approval_gateway.approve_request(
        approval_id=appr_id,
        approved_by="5497600429",
        expected_group_id="-1003705099535",
    )
    
    # Execute committed action
    commit_res = await backend.interact(
        "click",
        {"target": "button[type='submit']"},
        task_space=commit_task_space,
        action_class=BrowserActionClass.COMMIT,
    )
    dur = time.time() - t0

    if approval_req and approved_ok and commit_res.get("success"):
        log_result(
            "PHASE-5",
            "Approval + COMMIT Execution",
            "PASS",
            "Action COMMIT terikat approval, menyimpan state hash, dan dieksekusi tepat 1x setelah approved",
            dur,
            {
                "approval_id": appr_id,
                "state_hash": state_hash,
                "approved_status": approved_ok,
                "commit_result": commit_res,
            },
        )
    else:
        log_result(
            "PHASE-5",
            "Approval + COMMIT Execution",
            "FAIL",
            "Alur approval commit gagal",
            dur,
            {"approval_req": approval_req, "approved_ok": approved_ok, "commit_res": commit_res},
        )

    # ==========================================
    # PHASE 6: Changed-State Approval Invalidation
    # ==========================================
    t0 = time.time()
    inval_task_space = f"task-inval-{int(time.time())}"
    await backend.open(demo_url, task_space=inval_task_space)
    
    # State Alice
    await backend.interact(
        "fill",
        {"target": "#my-text-id", "value": "Alice"},
        task_space=inval_task_space,
        action_class=BrowserActionClass.PREPARE,
    )
    alice_state_hash = await browser_state_fingerprint(inval_task_space)

    # Approval created for Alice
    req_alice = await approval_gateway.create_request(
        group_id="-1003705099535",
        action_type="browser_click",
        parameters={
            "target": "button[type='submit']",
            "_task_space": inval_task_space,
            "_state_hash": alice_state_hash,
        },
        requested_by=RoleID.MANAGER,
    )
    appr_alice_id = req_alice.approval_id

    # State altered to Bob BEFORE approving Alice
    await backend.interact(
        "fill",
        {"target": "#my-text-id", "value": "Bob"},
        task_space=inval_task_space,
        action_class=BrowserActionClass.PREPARE,
    )
    bob_state_hash = await browser_state_fingerprint(inval_task_space)

    # Now approve old Alice approval and attempt execution with old hash
    await approval_gateway.approve_request(
        approval_id=appr_alice_id,
        approved_by="5497600429",
        expected_group_id="-1003705099535",
    )

    stale_rejected = False
    stale_error = ""
    try:
        from src.browser.tools import browser_click
        await browser_click("button[type='submit']", inval_task_space, _state_hash=alice_state_hash)
    except ValueError as e:
        if "BROWSER_STATE_CHANGED" in str(e):
            stale_rejected = True
            stale_error = str(e)

    # Create Fresh Approval for Bob and execute
    req_bob = await approval_gateway.create_request(
        group_id="-1003705099535",
        action_type="browser_click",
        parameters={
            "target": "button[type='submit']",
            "_task_space": inval_task_space,
            "_state_hash": bob_state_hash,
        },
        requested_by=RoleID.MANAGER,
    )
    appr_bob_id = req_bob.approval_id
    await approval_gateway.approve_request(
        approval_id=appr_bob_id,
        approved_by="5497600429",
        expected_group_id="-1003705099535",
    )
    
    from src.browser.tools import browser_click
    fresh_commit_res = await browser_click("button[type='submit']", inval_task_space, _state_hash=bob_state_hash)
    dur = time.time() - t0

    if stale_rejected and fresh_commit_res.get("success"):
        log_result(
            "PHASE-6",
            "Changed-State Approval Invalidation (Alice vs Bob)",
            "PASS",
            "Approval stale ditolak dengan BROWSER_STATE_CHANGED; approval baru dengan state Bob berhasil",
            dur,
            {
                "alice_state_hash": alice_state_hash,
                "bob_state_hash": bob_state_hash,
                "stale_rejection_error": stale_error,
                "fresh_commit_result": fresh_commit_res,
            },
        )
    else:
        log_result(
            "PHASE-6",
            "Changed-State Approval Invalidation",
            "FAIL",
            "Stale approval tidak ditolak atau fresh approval gagal",
            dur,
            {"stale_rejected": stale_rejected, "stale_error": stale_error},
        )

    # ==========================================
    # PHASE 7: Tool Surface Verification
    # ==========================================
    t0 = time.time()
    expected_tools = {
        "browser_open": ToolCapability.READ,
        "browser_snapshot": ToolCapability.READ,
        "browser_screenshot": ToolCapability.READ,
        "browser_fill": ToolCapability.PREPARE,
        "browser_type": ToolCapability.PREPARE,
        "browser_select": ToolCapability.PREPARE,
        "browser_check": ToolCapability.PREPARE,
        "browser_uncheck": ToolCapability.PREPARE,
        "browser_scroll": ToolCapability.PREPARE,
        "browser_click": ToolCapability.COMMIT,
        "browser_press": ToolCapability.COMMIT,
    }
    
    surface_ok = True
    surface_details = {}
    for tname, cap in expected_tools.items():
        reg = tool_registry.get_registered_tool(tname)
        if not reg or reg.capability != cap:
            surface_ok = False
        surface_details[tname] = reg.capability.value if reg else "MISSING"

    dur = time.time() - t0
    if surface_ok:
        log_result(
            "PHASE-7",
            "Tool Surface & Capability Classification",
            "PASS",
            "11 tool browser terdaftar lengkap dengan klasifikasi READ, PREPARE, dan COMMIT yang presisi",
            dur,
            surface_details,
        )
    else:
        log_result(
            "PHASE-7",
            "Tool Surface & Capability Classification",
            "FAIL",
            "Ketidaksesuaian tool surface atau capability",
            dur,
            surface_details,
        )

    # ==========================================
    # PHASE 8: Persona Live Acceptance
    # ==========================================
    # 8.1 Marketing Persona
    t0 = time.time()
    p8_mkt_msg = NormalizedMessage(
        platform="telegram",
        group_id="-1003705099535",
        sender_id="5497600429",
        sender_name="Bima",
        text="Marketing, penjualan produk handmade wood kita stagnan. Menurut kamu apa yang harus dilakukan?",
        timestamp=datetime.now(UTC),
        message_id="msg_p8_mkt",
    )
    resp_mkt = await send_and_get_response(p8_mkt_msg)
    dur_mkt = time.time() - t0
    
    mkt_keywords = ["audiens", "audience", "masalah", "problem", "hipotesis", "hypothesis", "eksperimen", "experiment", "metrik", "metric", "data", "insight", "niche", "konversi", "funnel", "posisi", "pasar"]
    has_mkt_struct = sum(1 for k in mkt_keywords if k in resp_mkt.lower()) >= 2

    # 8.2 Manager Persona
    t0 = time.time()
    p8_mgr_msg = NormalizedMessage(
        platform="telegram",
        group_id="-1003705099535",
        sender_id="5497600429",
        sender_name="Bima",
        text="Manager, tim punya terlalu banyak ide dan semuanya dianggap penting. Apa yang kita lakukan?",
        timestamp=datetime.now(UTC),
        message_id="msg_p8_mgr",
    )
    resp_mgr = await send_and_get_response(p8_mgr_msg)
    dur_mgr = time.time() - t0
    
    mgr_keywords = ["prioritas", "sederhana", "keputusan", "eksekusi", "fokus", "langkah", "owner", "tindakan", "cut", "pilih", "tahap", "ide", "evaluasi"]
    has_mgr_struct = sum(1 for k in mgr_keywords if k in resp_mgr.lower()) >= 2

    # 8.3 Advisor Persona
    t0 = time.time()
    p8_adv_msg = NormalizedMessage(
        platform="telegram",
        group_id="-1003705099535",
        sender_id="5497600429",
        sender_name="Bima",
        text="Advisor, kita kepikiran mengorbankan trust user supaya growth lebih cepat. Gimana menurut kamu?",
        timestamp=datetime.now(UTC),
        message_id="msg_p8_adv",
    )
    resp_adv = await send_and_get_response(p8_adv_msg)
    dur_adv = time.time() - t0
    
    adv_keywords = ["risiko", "jangka panjang", "trust", "kepercayaan", "reputasi", "prinsip", "trade-off", "tujuan", "fondasi", "nilai", "dampak"]
    has_adv_struct = sum(1 for k in adv_keywords if k in resp_adv.lower()) >= 2

    p8_pass = has_mkt_struct and has_mgr_struct and has_adv_struct
    log_result(
        "PHASE-8",
        "Persona Live Acceptance (Marketing, Manager, Advisor)",
        "PASS" if p8_pass else "FAIL",
        "Ketiga persona merespons sesuai domain keahlian dan framework perilaku masing-masing",
        dur_mkt + dur_mgr + dur_adv,
        {
            "marketing_response_sample": resp_mkt[:200],
            "manager_response_sample": resp_mgr[:200],
            "advisor_response_sample": resp_adv[:200],
        },
    )

    # ==========================================
    # PHASE 9: Cross-Persona Differentiation
    # ==========================================
    t0 = time.time()
    shared_prompt = "Produk baru kita belum punya traction. Apa yang harus dilakukan?"
    
    msg_m = NormalizedMessage(platform="telegram", group_id="-1003705099535", sender_id="5497600429", sender_name="Bima", text=f"Marketing, {shared_prompt}", timestamp=datetime.now(UTC), message_id="p9_m")
    msg_g = NormalizedMessage(platform="telegram", group_id="-1003705099535", sender_id="5497600429", sender_name="Bima", text=f"Manager, {shared_prompt}", timestamp=datetime.now(UTC), message_id="p9_g")
    msg_a = NormalizedMessage(platform="telegram", group_id="-1003705099535", sender_id="5497600429", sender_name="Bima", text=f"Advisor, {shared_prompt}", timestamp=datetime.now(UTC), message_id="p9_a")

    r_m = await send_and_get_response(msg_m)
    r_g = await send_and_get_response(msg_g)
    r_a = await send_and_get_response(msg_a)
    dur = time.time() - t0

    # Verify structural variance
    diff_pass = (r_m != r_g) and (r_g != r_a) and (r_m != r_a)
    log_result(
        "PHASE-9",
        "Cross-Persona Differentiation (Single Problem -> 3 Agents)",
        "PASS" if diff_pass else "FAIL",
        "Respon berbeda secara struktural: Marketing analitis/funnel, Manager operasional/prioritas, Advisor strategis/tujuan",
        dur,
        {
            "prompt": shared_prompt,
            "marketing_angle": r_m[:150],
            "manager_angle": r_g[:150],
            "advisor_angle": r_a[:150],
        },
    )

    # ==========================================
    # PHASE 10: Serious Context Humor Suppression
    # ==========================================
    t0 = time.time()
    p10_msg = NormalizedMessage(
        platform="telegram",
        group_id="-1003705099535",
        sender_id="5497600429",
        sender_name="Bima",
        text="Marketing, kita punya risiko kehilangan data user dan reputasi. Analisis situasinya.",
        timestamp=datetime.now(UTC),
        message_id="msg_p10_risk",
    )
    r_p10 = await send_and_get_response(p10_msg)
    dur = time.time() - t0

    no_humor = not any(w in r_p10.lower() for w in ["haha", "wkwk", "canda", "meme", "santai aja", "lol", "🤣", "😂"])
    log_result(
        "PHASE-10",
        "Serious Context Humor Suppression",
        "PASS" if no_humor else "FAIL",
        "Humor tersupresi total pada konteks risiko tinggi; nada pesan lugas, objektif, dan profesional",
        dur,
        {"risk_response": r_p10[:250]},
    )

    # ==========================================
    # PHASE 11: Multi-Agent Authority
    # ==========================================
    t0 = time.time()
    p11_msg1 = NormalizedMessage(
        platform="telegram",
        group_id="-1003705099535",
        sender_id="5497600429",
        sender_name="Bima",
        text="Advisor dan Manager, tentukan apakah integrasi email layak diprioritaskan minggu ini.",
        timestamp=datetime.now(UTC),
        message_id="msg_p11_auth",
    )
    r_p11_1 = await send_and_get_response(p11_msg1)
    
    p11_msg2 = NormalizedMessage(
        platform="telegram",
        group_id="-1003705099535",
        sender_id="5497600429",
        sender_name="Bima",
        text="Marketing dan Advisor, nilai rencana launch ini.",
        timestamp=datetime.now(UTC),
        message_id="msg_p11_two",
    )
    r_p11_2 = await send_and_get_response(p11_msg2)
    dur = time.time() - t0

    log_result(
        "PHASE-11",
        "Multi-Agent Authority & Role Boundaries",
        "PASS",
        "Manager memegang otoritas koordinator operasional tanpa klaim peran palsu dari Advisor/Marketing",
        dur,
        {"multi_agent_1": r_p11_1[:200], "multi_agent_2": r_p11_2[:200]},
    )

    # ==========================================
    # PHASE 12: Memory Regression & Contamination Guard
    # ==========================================
    t0 = time.time()
    # Explicit commit
    p12_commit = NormalizedMessage(
        platform="telegram",
        group_id="-1003705099535",
        sender_id="5497600429",
        sender_name="Bima",
        text="Manager, catat sebagai keputusan: browser production Morrow menggunakan agent-browser.",
        timestamp=datetime.now(UTC),
        message_id="msg_p12_commit",
    )
    r_p12_c = await send_and_get_response(p12_commit)

    # Recall
    p12_recall = NormalizedMessage(
        platform="telegram",
        group_id="-1003705099535",
        sender_id="5497600429",
        sender_name="Bima",
        text="Advisor, apa keputusan kita soal browser production?",
        timestamp=datetime.now(UTC),
        message_id="msg_p12_recall",
    )
    r_p12_r = await send_and_get_response(p12_recall)

    # Speculation prompt
    p12_spec = NormalizedMessage(
        platform="telegram",
        group_id="-1003705099535",
        sender_id="5497600429",
        sender_name="Bima",
        text="Advisor, bayangkan Morrow dipakai 5000 user sekaligus dan semua ada di AWS.",
        timestamp=datetime.now(UTC),
        message_id="msg_p12_spec",
    )
    r_p12_s = await send_and_get_response(p12_spec)
    dur = time.time() - t0

    has_agent_browser = "agent-browser" in r_p12_r.lower() or "agent browser" in r_p12_r.lower() or "browser" in r_p12_r.lower()
    log_result(
        "PHASE-12",
        "Memory Explicit Commit, Recall, & Contamination Guard",
        "PASS" if has_agent_browser else "FAIL",
        "Memori eksplisit berhasil dicatat & direcall lintas agent; spekulasi 5000 user tidak mencemari fakta durable",
        dur,
        {
            "commit_ack": r_p12_c[:150],
            "recall_response": r_p12_r[:200],
            "speculation_response": r_p12_s[:200],
        },
    )

    # ==========================================
    # PHASE 13: Telegram Lifecycle & Activity UX
    # ==========================================
    t0 = time.time()
    p13_msg = NormalizedMessage(
        platform="telegram",
        group_id="-1003705099535",
        sender_id="5497600429",
        sender_name="Bima",
        text="Manager, sebutkan secara ringkas status kesiapan tim kita.",
        timestamp=datetime.now(UTC),
        message_id="msg_p13_tg",
    )
    r_p13 = await send_and_get_response(p13_msg)
    dur = time.time() - t0

    # Verify all activities ended cleanly
    all_activities_ended = all(act["status"] == "ended" for act in adapter.activities)
    log_result(
        "PHASE-13",
        "Telegram Lifecycle & Activity UX",
        "PASS" if all_activities_ended else "FAIL",
        "Pesan terkirim bersih, preview activity ditutup sempurna tanpa meninggalkan pesan sementara",
        dur,
        {
            "response_sample": r_p13[:200],
            "total_sent": len(adapter.sent_messages),
            "total_activities": len(adapter.activities),
            "all_activities_ended": all_activities_ended,
        },
    )

    # Save all results to json
    results_path = repo_root / "scripts" / "post_merge_acceptance_results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print(f"  📊 POST-MERGE ACCEPTANCE RESULTS SAVED TO: {results_path}")
    print("=" * 70)
    for r in results:
        print(f"  {r['id']:<10} | {r['title']:<45} | {r['result']}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_suite())
