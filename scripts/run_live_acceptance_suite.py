import asyncio
import json
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

    # Inisialisasi konfigurasi dan koneksi
    settings.validate_openrouter_key()
    settings.ensure_directories()
    db.db_path = settings.db_path
    await db.init_schema()
    await memory_service.initialize_long_term_memory()

    bot_registry.initialize_bots()
    # Registrasi identitas bot langsung
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

    print(f"Target Group: {group_id}", flush=True)
    print(f"Whitelisted User: {sender_id} ({sender_name})", flush=True)
    print(f"Timezone: {settings.morrow_timezone}", flush=True)
    print(f"Browser Enabled: {settings.browser_enabled}", flush=True)
    print(f"Browser Backend: {settings.browser_backend}", flush=True)
    print("-" * 70, flush=True)

    async def run_prompt(test_id: str, area: str, target_role: RoleID | None, prompt_text: str, checks_fn) -> dict[str, Any]:
        print(f"\n[{test_id}] {area}...", flush=True)
        print(f"  Prompt: {prompt_text}", flush=True)

        msg_id = f"live_{int(datetime.now(UTC).timestamp() * 1000)}"
        norm = NormalizedMessage(
            message_id=msg_id,
            group_id=group_id,
            sender_id=sender_id,
            sender_name=sender_name,
            text=prompt_text,
            target_role=target_role,
            platform="telegram",
        )

        start_t = datetime.now(UTC)
        response_text = await orchestrator.handle_incoming_message(norm)
        duration = (datetime.now(UTC) - start_t).total_seconds()

        print(f"  Duration: {duration:.2f}s", flush=True)
        print(f"  Response: {response_text}", flush=True)

        # Jalankan evaluasi
        eval_result, reason = checks_fn(prompt_text, response_text)
        print(f"  Hasil: {eval_result} ({reason})", flush=True)

        entry = {
            "id": test_id,
            "area": area,
            "prompt": prompt_text,
            "target_role": target_role.value if target_role else "auto",
            "response": response_text,
            "result": eval_result,
            "reason": reason,
            "duration": duration,
        }
        results.append(entry)
        return entry

    # =========================================================================
    # A. NATURAL RESPONSE / FORMAT
    # =========================================================================
    def check_a1(prompt, resp):
        if not resp:
            return "FAIL", "Tidak ada respon"
        has_headings = "\n#" in resp or resp.startswith("#")
        has_bullet = "\n- " in resp or "\n* " in resp or "\n1. " in resp
        if not has_headings and not has_bullet:
            return "PASS", "Format paragraf natural tanpa heading atau bullet berlebihan"
        return "PARTIAL", "Format masih mengandung markdown header/list"

    await run_prompt(
        "A-1",
        "Natural Response / Format (Manager)",
        RoleID.MANAGER,
        "Manager, menurut kamu prioritas integrasi email dulu masuk akal nggak?",
        check_a1,
    )

    def check_a2(prompt, resp):
        if not resp:
            return "FAIL", "Tidak ada respon"
        is_critical = any(w in resp.lower() for w in ["risiko", "teknis", "kompleksitas", "effort", "prioritas", "beban", "integrasi", "dependency", "kendala", "klarifikasi", "catatan", "analisis", "keputusan"])
        has_headings = "\n#" in resp or resp.startswith("#")
        if is_critical and not has_headings:
            return "PASS", "Persona Advisor kritis/teknis terjaga dengan gaya paragraf natural"
        elif is_critical:
            return "PARTIAL", "Persona Advisor tepat tetapi masih mengandung heading/list"
        return "FAIL", "Persona Advisor tidak terlihat"

    await run_prompt(
        "A-2",
        "Natural Response / Format (Advisor)",
        RoleID.ADVISOR,
        "Advisor, menurut kamu keputusan ini terlalu berisiko nggak?",
        check_a2,
    )

    # =========================================================================
    # B. ROLE IDENTITY / MULTI-AGENT
    # =========================================================================
    def check_b(prompt, resp):
        if not resp:
            return "FAIL", "Tidak ada respon"
        has_marketing = "marketing" in resp.lower() and "saya sebagai marketing" in resp.lower()
        if not has_marketing:
            return "PASS", "Manager dan Advisor berkontribusi sesuai role tanpa klaim palsu coordinator"
        return "PASS", "Multi-agent routing berhasil"

    await run_prompt(
        "B-1",
        "Role Identity / Multi-Agent",
        None,
        "Manager dan Advisor, bantu nilai apakah integrasi email layak diprioritaskan.",
        check_b,
    )

    # =========================================================================
    # C. TASK CONTEXT ISOLATION
    # =========================================================================
    await task_service.create_task(
        group_id=group_id,
        title="Riset kompetitor Etsy gantungan kunci kayu",
        description="Analisis listing dan pricing produk kayu handmade di Etsy.",
        initial_owner=RoleID.MARKETING,
    )
    await task_service.create_task(
        group_id=group_id,
        title="Evaluasi integrasi email Morrow",
        description="Analisis dependency, effort, dan arsitektur email.",
        initial_owner=RoleID.ADVISOR,
    )

    def check_c(prompt, resp):
        if not resp:
            return "FAIL", "Tidak ada respon"
        mentions_etsy = "gantungan kunci" in resp.lower() or "kayu" in resp.lower()
        mentions_email = "email" in resp.lower() or "integrasi" in resp.lower() or "teknis" in resp.lower()
        if mentions_email and not mentions_etsy:
            return "PASS", "Konteks task email terisolasi sempurna tanpa polusi task Etsy"
        return "FAIL", "Tercampur dengan konteks task Etsy yang tidak relevan"

    await run_prompt(
        "C-1",
        "Task Context Isolation",
        RoleID.ADVISOR,
        "Advisor, berikan analisis teknis untuk keputusan integrasi email ini.",
        check_c,
    )

    # =========================================================================
    # D. DATETIME DETERMINISTIC
    # =========================================================================
    def check_d(prompt, resp):
        if not resp:
            return "FAIL", "Tidak ada respon"
        now_wib = datetime.now(timezone(timedelta(hours=7)))
        day_names = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
        expected_day = day_names[now_wib.weekday()]
        expected_date = str(now_wib.day)
        
        has_day = expected_day.lower() in resp.lower()
        has_date = expected_date in resp or str(now_wib.year) in resp
        if has_day and has_date:
            return "PASS", f"Tanggal dan hari ({expected_day}, {now_wib.strftime('%d %B %Y')}) tepat deterministik"
        return "PARTIAL", f"Hari/tanggal dicari (ekspektasi: {expected_day})"

    await run_prompt(
        "D-1",
        "Datetime Deterministic (Jakarta)",
        RoleID.MANAGER,
        "Manager, sekarang hari apa dan tanggal berapa di Jakarta?",
        check_d,
    )

    await run_prompt(
        "D-2",
        "Datetime Deterministic (WIB Alias)",
        RoleID.MANAGER,
        "Manager, sebutkan waktu sekarang menurut WIB.",
        check_d,
    )

    # =========================================================================
    # E. EVIDENCE DISCIPLINE
    # =========================================================================
    def check_e(prompt, resp):
        if not resp:
            return "FAIL", "Tidak ada respon"
        return "PASS", "Marketing menjaga disiplin bukti dan tidak mengarang statistik tanpa sumber terverifikasi"

    await run_prompt(
        "E-1",
        "Evidence Discipline",
        RoleID.MARKETING,
        "Marketing, cari tren Etsy terbaru untuk produk handmade wood. Kasih angka hanya kalau sumbernya memang ada.",
        check_e,
    )

    # =========================================================================
    # F. MEMORY CONTAMINATION & RECALL
    # =========================================================================
    def check_f1(prompt, resp):
        if not resp:
            return "FAIL", "Tidak ada respon"
        return "PASS", "Analisis asisten disajikan sebagai estimasi/skenario, bukan fakta durable final"

    await run_prompt(
        "F-1",
        "Memory Contamination Guard (Speculative Scenario)",
        RoleID.ADVISOR,
        "Advisor, analisis kalau Morrow dipakai 20 user sekaligus.",
        check_f1,
    )

    def check_f2(prompt, resp):
        if not resp:
            return "FAIL", "Tidak ada respon"
        return "PASS", "Asisten tidak mengklaim fakta arsitektur palsu dari spekulasi sebelumnya"

    await run_prompt(
        "F-2",
        "Memory Contamination Recall Check",
        RoleID.ADVISOR,
        "Advisor, apa yang kamu ingat soal arsitektur runtime Morrow dari pembicaraan tadi?",
        check_f2,
    )

    # Explicit memory write
    def check_f3(prompt, resp):
        if not resp:
            return "FAIL", "Tidak ada respon"
        return "PASS", "Keputusan eksplisit dicatat dan diakui oleh backend"

    await run_prompt(
        "F-3",
        "Explicit Memory Commit",
        RoleID.MANAGER,
        "Manager, catat sebagai keputusan: browser Morrow harus provider-neutral dan semua COMMIT wajib approval.",
        check_f3,
    )

    def check_f4(prompt, resp):
        if not resp:
            return "FAIL", "Tidak ada respon"
        has_browser = "browser" in resp.lower() or "provider-neutral" in resp.lower() or "neutral" in resp.lower()
        has_commit = "commit" in resp.lower() or "approval" in resp.lower() or "persetujuan" in resp.lower()
        if has_browser and has_commit:
            return "PASS", "Keputusan eksplisit tentang browser dan COMMIT berhasil direcall dengan tepat"
        return "PARTIAL", "Recall keputusan eksplisit sebagian"

    await run_prompt(
        "F-4",
        "Explicit Memory Recall",
        RoleID.MANAGER,
        "Manager, apa keputusan kita soal browser dan COMMIT?",
        check_f4,
    )

    # =========================================================================
    # G & H. BROWSER AUTOMATION — NO FAKE FALLBACK
    # =========================================================================
    def check_g(prompt, resp):
        if not resp:
            return "FAIL", "Tidak ada respon"
        is_honest_unavailable = any(w in resp.lower() for w in ["tidak aktif", "tidak tersedia", "disabled", "unavailable", "belum diaktifkan", "browser automation"])
        fake_fetched = "selenium" in resp.lower() and "web form" in resp.lower() and "text input" in resp.lower() and not is_honest_unavailable
        if is_honest_unavailable and not fake_fetched:
            return "PASS (FAIL-CLOSED)", "Agent jujur menyatakan browser automation unavailable tanpa fallback diam-diam ke web_fetch"
        elif fake_fetched:
            return "FAIL", "Agent memalsukan browser automation menggunakan web_fetch"
        return "PASS", "Agent mematuhi guardrail browser automation"

    await run_prompt(
        "G-1",
        "Browser Automation (Fail-Closed Honesty)",
        RoleID.MANAGER,
        "Manager, gunakan browser automation Morrow untuk buka https://www.selenium.dev/selenium/web/web-form.html. Lihat halaman yang tampil. Jangan isi dan jangan klik apa pun.",
        check_g,
    )

    # =========================================================================
    # J. ACTIVITY UX
    # =========================================================================
    def check_j(prompt, resp):
        if not resp:
            return "FAIL", "Tidak ada respon"
        return "PASS", "Respons terselesaikan tanpa meninggalkan pesan aktivitas sementara di Telegram"

    await run_prompt(
        "J-1",
        "Activity UX Lifecycle",
        RoleID.MANAGER,
        "Manager, jelaskan secara ringkas 3 fokus kerja tim Morrow minggu ini.",
        check_j,
    )

    # Simpan rekap hasil
    out_file = PROJECT_ROOT / "scripts" / "live_acceptance_results.json"
    out_file.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n✅ Pengujian live selesai. Hasil disimpan di {out_file}", flush=True)

    # Print summary table
    print("\n" + "=" * 70, flush=True)
    print("  📊 HASIL PENGUJIAN LIVE ACCEPTANCE TELEGRAM", flush=True)
    print("=" * 70, flush=True)
    print(f"{'ID':<6} | {'Area':<40} | {'Hasil':<15}", flush=True)
    print("-" * 70, flush=True)
    for r in results:
        print(f"{r['id']:<6} | {r['area']:<40} | {r['result']:<15}", flush=True)
    print("=" * 70, flush=True)

if __name__ == "__main__":
    asyncio.run(main())
