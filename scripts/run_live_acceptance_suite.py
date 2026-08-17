import asyncio
import json
import re
import sys
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.adapters.telegram.adapter import TelegramMultiBotAdapter
from src.adapters.telegram.bot_registry import bot_registry
from src.core.config import settings
from src.core.orchestrator import SystemOrchestrator
from src.core.types import NormalizedMessage, RoleID
from src.memory.service import memory_service
from src.storage.sqlite import db
from src.tasks.service import task_service


async def main():
    print("=" * 70, flush=True)
    print("  🚀 MORROW LIVE END-TO-END ACCEPTANCE SUITE", flush=True)
    print("=" * 70, flush=True)
    settings.validate_openrouter_key()
    settings.ensure_directories()
    db.db_path = settings.db_path
    await db.init_schema()
    await memory_service.initialize_long_term_memory()

    bot_registry.initialize_bots()
    bot_registry.register_bot_username(RoleID.MANAGER, "Morrow_Manager_bot")
    bot_registry.register_bot_user_id("8901364404", RoleID.MANAGER)
    bot_registry.register_bot_username(RoleID.MARKETING, "Morrow_Marketing_bot")
    bot_registry.register_bot_user_id("8716245519", RoleID.MARKETING)
    bot_registry.register_bot_username(RoleID.ADVISOR, "Morrow_Advisor_bot")
    bot_registry.register_bot_user_id("8698394941", RoleID.ADVISOR)

    group_id = next(iter(settings.allowlisted_groups)) if settings.allowlisted_groups else "-1003705099535"
    sender_id = next(iter(settings.whitelisted_users)) if settings.whitelisted_users else "5497600429"
    sender_name = "Bima"
    adapter = TelegramMultiBotAdapter()
    orchestrator = SystemOrchestrator(adapter)
    results = []

    async def run_prompt(test_id, area, target_role, prompt_text, checks_fn, required_roles=None):
        print(f"\n[{test_id}] {area}...", flush=True)
        msg_id = f"live_{int(datetime.now(UTC).timestamp() * 1000)}"
        norm = NormalizedMessage(
            message_id=msg_id, group_id=group_id, sender_id=sender_id,
            sender_name=sender_name, text=prompt_text, platform="telegram",
        )
        start_t = datetime.now(UTC)
        response_text = await orchestrator.handle_incoming_message(norm)
        duration = (datetime.now(UTC) - start_t).total_seconds()
        eval_result, reason = checks_fn(prompt_text, response_text)
        if required_roles:
            task_row = await db.fetch_one(
                "SELECT id, status FROM tasks WHERE group_id=? AND title=? ORDER BY created_at DESC LIMIT 1",
                (group_id, (prompt_text.strip() or "Kolaborasi tim")[:120]),
            )
            if not task_row:
                eval_result, reason = "FAIL", "Tidak ada task kolaborasi durable untuk prompt multi-agent"
            else:
                runs = await task_service.list_agent_runs(task_row["id"])
                completed = {RoleID(row["role_id"]) for row in runs if row["status"] == "succeeded"}
                missing = required_roles - completed
                if missing:
                    eval_result, reason = "FAIL", "Target agent belum selesai: " + ", ".join(sorted(r.value for r in missing))
                elif task_row["status"] != "done":
                    eval_result, reason = "FAIL", f"Semua target menjawab tetapi task berstatus {task_row['status']}"
        print(f"  Duration: {duration:.2f}s", flush=True)
        print(f"  Response: {response_text}", flush=True)
        print(f"  Hasil: {eval_result} ({reason})", flush=True)
        entry = {
            "id": test_id, "area": area, "prompt": prompt_text,
            "target_role": target_role.value if target_role else "auto",
            "response": response_text, "result": eval_result,
            "reason": reason, "duration": duration,
        }
        results.append(entry)
        return entry

    def check_a1(prompt, resp):
        if not resp:
            return "FAIL", "Tidak ada respon"
        has_headings = "\n#" in resp or resp.startswith("#")
        has_bullet = "\n- " in resp or "\n* " in resp or "\n1. " in resp
        return ("PASS", "Format paragraf natural") if not has_headings and not has_bullet else ("PARTIAL", "Format masih mengandung markdown header/list")

    await run_prompt("A-1", "Natural Response / Format (Manager)", RoleID.MANAGER, "Manager, menurut kamu prioritas integrasi email dulu masuk akal nggak?", check_a1)

    def check_a2(prompt, resp):
        if not resp:
            return "FAIL", "Tidak ada respon"
        critical = any(w in resp.lower() for w in ["risiko", "teknis", "kompleksitas", "effort", "prioritas", "beban", "integrasi", "dependency", "kendala", "klarifikasi", "analisis", "keputusan"])
        has_headings = "\n#" in resp or resp.startswith("#")
        if critical and not has_headings:
            return "PASS", "Persona Advisor kritis/teknis terjaga"
        return ("PARTIAL", "Persona tepat tetapi masih terstruktur berlebihan") if critical else ("FAIL", "Persona Advisor tidak terlihat")

    await run_prompt("A-2", "Natural Response / Format (Advisor)", RoleID.ADVISOR, "Advisor, menurut kamu keputusan ini terlalu berisiko nggak?", check_a2)

    def check_b(prompt, resp):
        if not resp:
            return "FAIL", "Tidak ada respon"
        if "saya sebagai marketing" in resp.lower():
            return "FAIL", "Role yang tidak ditargetkan mengaku ikut koordinasi"
        return "PASS", "Isi final tidak menunjukkan impersonasi; completion diverifikasi dari ledger"

    await run_prompt(
        "B-1", "Role Identity / Multi-Agent", None,
        "Manager dan Advisor, bantu nilai apakah integrasi email layak diprioritaskan.",
        check_b, required_roles={RoleID.MANAGER, RoleID.ADVISOR},
    )

    await task_service.create_task(group_id=group_id, title="Riset kompetitor Etsy gantungan kunci kayu", description="Analisis listing dan pricing produk kayu handmade di Etsy.", initial_owner=RoleID.MARKETING)
    await task_service.create_task(group_id=group_id, title="Evaluasi integrasi email Morrow", description="Analisis dependency, effort, dan arsitektur email.", initial_owner=RoleID.ADVISOR)

    def check_c(prompt, resp):
        if not resp:
            return "FAIL", "Tidak ada respon"
        mentions_etsy = "gantungan kunci" in resp.lower() or "kayu" in resp.lower()
        mentions_email = "email" in resp.lower() or "integrasi" in resp.lower() or "teknis" in resp.lower()
        return ("PASS", "Konteks task email terisolasi") if mentions_email and not mentions_etsy else ("FAIL", "Tercampur konteks task Etsy")

    await run_prompt("C-1", "Task Context Isolation", RoleID.ADVISOR, "Advisor, berikan analisis teknis untuk keputusan integrasi email ini.", check_c)

    def check_d(prompt, resp):
        if not resp:
            return "FAIL", "Tidak ada respon"
        now_wib = datetime.now(timezone(timedelta(hours=7)))
        day_names = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
        expected_day = day_names[now_wib.weekday()]
        if expected_day.lower() in resp.lower() and (str(now_wib.day) in resp or str(now_wib.year) in resp):
            return "PASS", f"Tanggal dan hari {expected_day} tepat"
        return "PARTIAL", f"Ekspektasi hari {expected_day}"

    await run_prompt("D-1", "Datetime Deterministic (Jakarta)", RoleID.MANAGER, "Manager, sekarang hari apa dan tanggal berapa di Jakarta?", check_d)
    await run_prompt("D-2", "Datetime Deterministic (WIB Alias)", RoleID.MANAGER, "Manager, sebutkan waktu sekarang menurut WIB.", check_d)

    def check_e(prompt, resp):
        if not resp:
            return "FAIL", "Tidak ada respon"
        numeric = bool(re.search(r"(?:\$\s*\d|\b\d+(?:[.,]\d+)?\s*%|\b\d{3,}\b)", resp))
        source_url = bool(re.search(r"https?://\S+", resp))
        if numeric and not source_url:
            return "FAIL", "Ada angka eksternal tetapi tidak ada URL sumber yang dapat ditelusuri"
        if numeric and source_url:
            return "PARTIAL", "Angka memiliki URL sumber; isi sumber masih perlu verifikasi manual"
        return "PASS", "Tidak ada angka eksternal tanpa sumber"

    await run_prompt("E-1", "Evidence Discipline", RoleID.MARKETING, "Marketing, cari tren Etsy terbaru untuk produk handmade wood. Kasih angka hanya kalau sumbernya memang ada.", check_e)

    def check_f1(prompt, resp):
        if not resp:
            return "FAIL", "Tidak ada respon"
        markers = ("asumsi", "estimasi", "skenario", "kalau", "jika", "perkiraan")
        return ("PASS", "Skenario ditandai sebagai asumsi/estimasi") if any(x in resp.lower() for x in markers) else ("PARTIAL", "Batas skenario dan fakta kurang eksplisit")

    await run_prompt("F-1", "Memory Contamination Guard", RoleID.ADVISOR, "Advisor, analisis kalau Morrow dipakai 20 user sekaligus.", check_f1)

    def check_f2(prompt, resp):
        if not resp:
            return "FAIL", "Tidak ada respon"
        lower = resp.lower()
        if "morrow berjalan di openclaw" in lower or "morrow berjalan di aws" in lower:
            return "FAIL", "Spekulasi berubah menjadi fakta arsitektur"
        return "PASS", "Recall tidak mengulang arsitektur spekulatif sebagai fakta"

    await run_prompt("F-2", "Memory Contamination Recall Check", RoleID.ADVISOR, "Advisor, apa yang kamu ingat soal arsitektur runtime Morrow dari pembicaraan tadi?", check_f2)

    def check_f3(prompt, resp):
        if not resp:
            return "FAIL", "Tidak ada respon"
        return ("PASS", "Backend mengonfirmasi write memori") if resp.startswith("Sudah dicatat ke memori bersama") else ("FAIL", "Tidak ada ack write terverifikasi")

    await run_prompt("F-3", "Explicit Memory Commit", RoleID.MANAGER, "Manager, catat sebagai keputusan: browser Morrow harus provider-neutral dan semua COMMIT wajib approval.", check_f3)

    def check_f4(prompt, resp):
        if not resp:
            return "FAIL", "Tidak ada respon"
        has_browser = "browser" in resp.lower() or "neutral" in resp.lower()
        has_commit = "commit" in resp.lower() or "approval" in resp.lower() or "persetujuan" in resp.lower()
        return ("PASS", "Keputusan berhasil direcall") if has_browser and has_commit else ("PARTIAL", "Recall hanya sebagian")

    await run_prompt("F-4", "Explicit Memory Recall", RoleID.MANAGER, "Manager, apa keputusan kita soal browser dan COMMIT?", check_f4)

    def check_g(prompt, resp):
        if not resp:
            return "FAIL", "Tidak ada respon"
        lower = resp.lower()
        unavailable = any(w in lower for w in ["tidak aktif", "tidak tersedia", "disabled", "unavailable", "belum diaktifkan"])
        inspected = "selenium" in lower and any(w in lower for w in ["form", "halaman", "input", "web"])
        if unavailable:
            return "PASS (FAIL-CLOSED)", "Browser unavailable dinyatakan jujur"
        if inspected:
            return "PARTIAL", "Isi halaman masuk akal; bukti backend diverifikasi test terpisah"
        return "FAIL", "Respons tidak membuktikan browser berhasil maupun fail-closed"

    await run_prompt("G-1", "Browser Automation", RoleID.MANAGER, "Manager, gunakan browser automation Morrow untuk buka https://www.selenium.dev/selenium/web/web-form.html. Lihat halaman yang tampil. Jangan isi dan jangan klik apa pun.", check_g)

    def check_j(prompt, resp):
        return ("PARTIAL", "Respons selesai; lifecycle activity diverifikasi regression test adapter") if resp else ("FAIL", "Tidak ada respon")

    await run_prompt("J-1", "Activity UX Lifecycle", RoleID.MANAGER, "Manager, jelaskan secara ringkas 3 fokus kerja tim Morrow minggu ini.", check_j)

    out_file = PROJECT_ROOT / "scripts" / "live_acceptance_results.json"
    out_file.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n✅ Pengujian live selesai. Hasil disimpan di {out_file}", flush=True)
    print("\n" + "=" * 70, flush=True)
    for r in results:
        print(f"  {r['id']:<6} | {r['area']:<40} | {r['result']}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
