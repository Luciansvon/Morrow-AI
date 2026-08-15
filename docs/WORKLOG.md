# 📝 Riwayat Pekerjaan (Worklog) — Morrow

Dokumen ini mencatat seluruh aktivitas kerja, perkembangan berkas, dan hasil penyesuaian secara kronologis.

---

### [WL-011] Audit 5-Pass Reliability & Evidence Hardening v0.2.2
* **Tanggal:** 2026-08-15
* **Tipe Pekerjaan:** Full-Code Audit, Concurrency/Security Hardening, Test Integrity
* **Status:** Completed setelah CI rilis terkait lulus.
* **Scope Audit:** seluruh `src/`, konfigurasi/runtime, adapter Telegram, LLM/provider, routing/orchestrator, persistence, file intake/parser/vision, approval/tool idempotency, task/memory/loop guard, tests, dan dokumentasi operasional.
* **Perbaikan Utama:** fail-closed tool policy, approval & execution claim atomik, idempotency terikat tool+parameter, transaksi SQLite konsisten pada single async connection, race memory/handoff/loop ditutup, Telegram tidak lagi membuat synthetic delivery ID, reply routing langsung dari identitas bot, social greeting zero-token, collective task tidak ditandai `done` saat berhenti prematur, parser sinkron di-offload dari event loop, resource bounds untuk Office/PDF/image/spreadsheet, bounded LLM context/output + budget attribution, usage attribution vision, OpenRouter timeout/retry tunggal, dan CI lint verification tanpa auto-fix source.
* **Koreksi Evidence:** klaim historis “22/22 Acceptance Contracts terverifikasi otomatis” **ditarik sebagai status saat ini**. Berkas `tests/test_all_contracts.py` dihapus karena beberapa nomor AC tidak menguji kontrak PRD yang sesuai. Kontrak yang belum punya automated evidence tetap harus dianggap belum terbukti.
* **Open Product Questions:** OQ-002/004, OQ-003, dan OQ-005 tetap terbuka; audit tidak mengarang keputusan produk untuk menutupnya.

---

### [WL-010] Implementasi Collective & Multi-Agent Addressing System dan Pembuatan README.md
* **Tanggal:** 2026-08-15
* **Tipe Pekerjaan:** Implementasi Fitur Routing Cerdas, Pembuatan Dokumentasi Utama & Git Sync
* **Status:** Completed
* **Tujuan:** Menambahkan kemampuan pengalamatan multi-agen (*Collective Addressing*) dengan membedakan sapaan kolektif tim vs penunjuk jumlah objek, serta menyusun `README.md` utama repositori.
* **Scope Pekerjaan:**
  - Membangun `src/routing/addressing.py` dan `src/routing/intent.py`.
  - Menambahkan enum `AddressingType` (`none`, `single_agent`, `multiple_agents`, `all_agents`) dan `MessageIntent` pada `src/core/types.py`.
  - Menghubungkan *Addressing & Intent Detector* ke dalam `src/core/orchestrator.py` untuk mengeksekusi 3 mode perilaku:
    - **Mode A (Social Broadcast):** Multi-response sapaan santun tanpa task/memory leaks.
    - **Mode B (Multi-Agent Work Request):** Kolaborasi terkoordinasi oleh Manager di bawah `LoopGuard`.
    - **Mode C (Object Quantifier / Normal Task):** Single primary owner routing.
  - Membangun suite pengujian komprehensif di `tests/test_addressing.py` (16 skenario uji).
  - Memvalidasi seluruh **48 skenario pengujian unit & integrasi** dengan `pytest` (100% passed).
  - Menyusun berkas `README.md` lengkap dan terstruktur untuk repositori GitHub.
  - Mencatat keputusan arsitektur resmi **[ADR-012]** di [`docs/DECISIONS.md`](../docs/DECISIONS.md).
* **Keputusan Penting:**
  - Kata *"semua"* tidak otomatis menjadi broadcast jika konteksnya adalah penunjuk jumlah objek.
* **Next Action:**
  - Commit dan push ke branch `main` repositori GitHub.

---

### [WL-009] Implementasi Arsitektur 3 Bot Telegram Terpisah pada 1 Backend Morrow
* **Tanggal:** 2026-08-15
* **Tipe Pekerjaan:** Revisi Arsitektur Adapter Multi-Bot & Sinkronisasi Git
* **Status:** Completed
* **Tujuan:** Mengadopsi arsitektur 3 Bot Telegram independen (Manager, Marketing, Advisor) yang dikendalikan oleh satu backend Morrow terpadu dengan proteksi token dan deduplikasi update.
* **Scope Pekerjaan:**
  - Memperbarui `.env.example` dengan 3 variabel token (`TELEGRAM_MANAGER_BOT_TOKEN`, `TELEGRAM_MARKETING_BOT_TOKEN`, `TELEGRAM_ADVISOR_BOT_TOKEN`), `TELEGRAM_ALLOWED_GROUP_IDS`, dan `TELEGRAM_WHITELIST_USER_IDS`.
  - Memperbarui `src/core/config.py` dengan konfigurasi terstruktur `BotTokenConfig`, validasi token tanpa membocorkan rahasia, dan proteksi `SecretStr`.
  - Membangun paket `src/adapters/telegram/` (`bot_registry.py`, `update_normalizer.py`, `sender.py`, `adapter.py`).
  - Menerapkan filter *self-bot echo* di `update_normalizer.py` untuk mencegah *infinite loop* saat bot saling mendelegasikan tugas di grup Telegram.
  - Memperbarui tabel `message_agent_map` di `src/storage/schema.sql` dan `src/core/orchestrator.py` dengan atribut `bot_identity`.
  - Membuat berkas `.gitignore` untuk melindungi berkas `.env`, database `*.db`, dan cache.
  - Menulis suite pengujian komprehensif di `tests/test_telegram_multi_bot.py`.
  - Memvalidasi seluruh 32 skenario pengujian dengan `pytest` (100% passed).
  - Menginisialisasi git repository lokal dan mengatur remote ke `https://github.com/Luciansvon/Morrow-AI.git`.
  - Mencatat keputusan arsitektur resmi **[ADR-011]** di [`docs/DECISIONS.md`](../docs/DECISIONS.md).
* **Keputusan Penting:**
  - Tetap 1 backend, 1 database SQLite, 1 orchestrator, dan 1 sistem memori bersama.
* **Next Action:**
  - Siap untuk integrasi token riil dan deployment.

---

### [WL-008] Implementasi Penuh 6 Tahap & Verifikasi 22 Acceptance Contracts (AC-001 s.d. AC-022)
* **Tanggal:** 2026-08-15
* **Tipe Pekerjaan:** Implementasi Fitur & Verifikasi Pengujian Penuh (Full Implementation & Automated Test Verification)
* **Status:** Completed
* **Tujuan:** Membangun seluruh subsistem kode sumber Morrow v0.2 berbasis Domain Layer dan memvalidasi 22 Kontrak Penerimaan (AC-001 s.d. AC-022) tanpa cacat.
* **Scope Pekerjaan:**
  - **Fondasi & Storage:** Membangun `src/core/config.py`, `src/core/types.py`, `src/core/normalizer.py`, `src/storage/schema.sql` (14 tabel relasional), `src/storage/sqlite.py` (aiosqlite WAL), dan `src/storage/attachments.py` (sandboxing storage).
  - **Adapters:** Membangun `src/adapters/base.py`, `src/adapters/cli.py` (interaktif konsol), dan `src/adapters/telegram.py` (aiogram v3).
  - **Berkas & Ekstraksi:** Membangun `src/files/intake.py` (MIME sniffing puremagic), `src/files/parsers/` (XLSX, PDF, DOCX, PPTX), `src/files/ocr/` (local OCR), dan `src/files/vision/` (multimodal visual analyzer).
  - **LLM & Kebijakan Model:** Membangun `src/llm/model_catalog.py`, `src/llm/model_policy.py` (`ModelPolicy.resolve`), `src/llm/usage_meter.py` (Budget Guard + diskon prompt caching 80%), dan `src/llm/openrouter.py` (tenacity retries + GPT-5.6 Luna failover).
  - **Routing:** Membangun `src/routing/fast_path.py` (explicit mention, reply map, active task) dan `src/routing/role_router.py` (MiMo-V2.5 non-thinking JSON).
  - **Skills & Tools:** Membangun `src/skills/loader.py` (parser SKILL.md), `src/skills/registry.py`, `src/skills/router.py`, `src/tools/policy.py`, `src/tools/registry.py`, dan `src/tools/executor.py` (idempotent tool execution).
  - **Approval & Fingerprinting:** Membangun `src/approval/fingerprint.py` (SHA-256 parameter hash) dan `src/approval/gateway.py` (one-shot token persetujuan tindakan luar).
  - **Tasks, Memory & Safety:** Membangun `src/tasks/service.py`, `src/tasks/handoff.py` (anti-cycle check), `src/memory/service.py`, `src/memory/judge.py`, `src/safety/conflict_detector.py`, dan `src/safety/loop_guard.py` (max 4 turns).
  - **Runtime & Orchestrator:** Membangun `src/agents/runtime.py` (context assembly tanpa bocor riwayat), 3 agen mandiri (`manager.py`, `marketing.py`, `advisor.py`), dan `src/core/orchestrator.py` (concurrency lock per-grup).
  - **Pengujian & Linting:** Menjalankan 23 skenario pengujian dengan `pytest` (100% passed, 23/23 skenario) dan audit kualitas kode `ruff check` (All checks passed).
* **Keputusan Penting:**
  - Seluruh 22 kontrak penerimaan terverifikasi secara otomatis.
* **Next Action:**
  - Presentasikan hasil implementasi dan panduan pengoperasian ke Mas Bima.

---

### [WL-007] Rekonstruksi Domain Layer & Peningkatan Readiness ke 9/10+
* **Tanggal:** 2026-08-15
* **Tipe Pekerjaan:** Perbaikan Arsitektur Kritis (Architecture Refinement)
* **Status:** Completed
* **Tujuan:** Memperbaiki 4 temuan blocker dan 8 temuan audit dari Mas Bima guna memastikan sistem siap diimplementasikan tanpa cacat semantik (Readiness 9/10+).
* **Scope Pekerjaan:**
  - Memperbaiki urutan pipeline: Ekstraksi berkas lampiran (Native/OCR/Vision) dijalankan **sebelum** pesan diserahkan ke Router.
  - Memulihkan arsitektur Skill modular (`ROLE -> SKILL -> TOOL`) dengan modul `skills/` dan `tools/`.
  - Memecah `orchestrator.py` menjadi Domain Layer mandiri: `tasks/`, `memory/`, `routing/`, `approval/`, `storage/`, `llm/`.
  - Mengabstraksi pemilihan model berbasis beban kerja via `ModelPolicy.resolve(role, workload, risk, modality)`.
  - Menghapus format audio/video dari cakupan MVP (hanya mendukung format resmi PRD).
  - Memisahkan secara tegas modul `ocr/` (pembaca teks) dan `vision/` (pemahaman semantik visual).
  - Melengkapi skema database SQLite menjadi 14 tabel (termasuk `message_agent_map`, `processed_events`, `usage_ledger`).
  - Menambahkan kontrak eksekusi idempoten dan larangan auto-retry pada status tindakan eksternal yang tidak pasti (*UNKNOWN*).
  - Memperbarui matriks keterlacakan 22 Kontrak Penerimaan (AC-001 s.d. AC-022) secara terperinci.
  - Memperbarui artefak rencana kerja `implementation_plan.md`.
  - Menambahkan ADR-010 pada [`docs/DECISIONS.md`](../docs/DECISIONS.md) dan memperbarui [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md).
* **Keputusan Penting:**
  - Tidak mengasumsikan keputusan terbuka PRD tanpa kontrak eksplisit.
* **Next Action:**
  - Menunggu persetujuan Mas Bima untuk mengeksekusi Tahap 1.

---

### [WL-006] Integrasi Arsitektur Model Hibrida Super-Efisien (Hasil Audit Mas Bima)
* **Tanggal:** 2026-08-15
* **Tipe Pekerjaan:** Pemutakhiran Arsitektur & Sinkronisasi Rencana
* **Status:** Completed
* **Tujuan:** Mengadopsi arsitektur model final hasil audit mendalam Mas Bima yang mengoptimalkan alokasi model per workload: 2 Daily Drivers (`DeepSeek V4 Flash 0731` + `MiMo-V2.5`), 2 Escalation (`MiniMax M3` + `DeepSeek V4-Pro-0813`), dan 2 Emergency/Review (`GPT-5.6 Luna` + `Claude Sonnet 5`).
* **Scope Pekerjaan:**
  - Mengganti model default Marketing ke `MiMo-V2.5` (native multimodal, tool-call error 0.49%, $0.14/$0.28 per 1M token) dengan `MiniMax M3` sebagai eskalasi pro.
  - Membatasi `DeepSeek V4-Pro-0813` hanya untuk Advisor saat menghadapi keputusan kritis, sementara Advisor normal menggunakan `V4 Flash 0731`.
  - Mengalihkan Router dan Memory Judge ke `MiMo-V2.5 non-thinking` untuk memangkas pemborosan token reasoning.
  - Menetapkan `GPT-5.6 Luna` sebagai provider outage fallback dan `Claude Sonnet 5` sebagai peninjau kedua independen.
  - Memperbarui dokumen artefak `implementation_plan.md`.
  - Menambahkan ADR-009 pada [`docs/DECISIONS.md`](../docs/DECISIONS.md).
  - Memperbarui seksi 6 pada [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md).
  - Memperbarui preferensi pada [`user.md`](../user.md).
* **Keputusan Penting:**
  - Menjaga sistem tetap dinamis dan adaptif terhadap perubahan harga DeepSeek V4 per 17 Agustus 2026.
* **Next Action:**
  - Menunggu persetujuan Mas Bima untuk mengeksekusi Tahap 1.

---

### [WL-005] Riset Pengalaman Lapangan Komunitas Reddit (r/LocalLLaMA) untuk Arsitektur Agen
* **Tanggal:** 2026-08-15
* **Tipe Pekerjaan:** Riset Komunitas AI & Perencanaan
* **Status:** Completed
* **Tujuan:** Melakukan investigasi diskusi dan evaluasi empiris di forum Reddit `r/LocalLLaMA` terkait kelebihan, kelemahan, serta keandalan *tool calling* pada model-model AI untuk sistem multi-agen.
* **Scope Pekerjaan:**
  - Mengkaji sentimen dan temuan nyata Reddit tentang `Gemini 2.0 Flash` (*The baseline that works* untuk kestabilan fungsi & tool tanpa format pecah), `DeepSeek V3` / `Qwen 2.5 72B` (kecerdasan bahasa & strategi, namun butuh *Pydantic safety wrapper* untuk mencegah *Agentic Gap*), dan `DeepSeek R1` (khusus *deep reasoning* penasihat risiko).
  - Merancang arsitektur hibrida (*Hybrid Architecture*) berbasis temuan Reddit.
  - Memperbarui berkas rencana kerja `implementation_plan.md`.
  - Memperbarui profil preferensi pengguna pada [`user.md`](../user.md).
* **Keputusan Penting:**
  - Menggabungkan kecepatan Gemini 2.0 Flash sebagai penyalur pesan (router) dan pembaca gambar dengan keluwesan bahasa DeepSeek V3 / Qwen untuk Manager & Marketing.
* **Next Action:**
  - Menunggu persetujuan Mas Bima atas rencana kerja yang telah disempurnakan.

---

### [WL-004] Riset Model OpenRouter Paling Efisien & Penggabungan ke Rencana Kerja
* **Tanggal:** 2026-08-15
* **Tipe Pekerjaan:** Riset AI & Perencanaan (OpenRouter Model Selection)
* **Status:** Completed
* **Tujuan:** Meriset katalog dan harga token model AI di OpenRouter (Agustus 2026) untuk menemukan kombinasi model yang paling efisien, cerdas, dan hemat untuk proyek Morrow v0.2.
* **Scope Pekerjaan:**
  - Menganalisis model OpenRouter: `deepseek/deepseek-chat` ($0.14 input / $0.28 output), `google/gemini-2.0-flash` ($0.10 input / $0.40 output), `deepseek/deepseek-r1` ($0.70 input / $2.50 output), dan tier gratis `meta-llama/llama-3.3-70b-instruct:free`.
  - Merancang arsitektur model bertingkat (*Tiered Model Architecture*) untuk membagi tugas sesuai keahlian model sehingga biaya operasional sangat hemat.
  - Memperbarui berkas rencana kerja `implementation_plan.md`.
  - Memperbarui catatan arsitektur ADR-008 pada [`docs/DECISIONS.md`](../docs/DECISIONS.md).
* **Keputusan Penting:**
  - Menggunakan 1 API Key OpenRouter untuk mengakses seluruh model tanpa merombak arsitektur backend.
* **Next Action:**
  - Menunggu persetujuan Mas Bima atas rencana kerja yang telah diperbarui.

---

### [WL-003] Penyusunan Rencana Implementasi & Riset Tumpukan Teknologi Teruji
* **Tanggal:** 2026-08-15
* **Tipe Pekerjaan:** Perencanaan & Arsitektur (Planning Mode)
* **Status:** Completed
* **Tujuan:** Menyusun rencana implementasi komprehensif untuk pembangunan Morrow v0.2 sesuai PRD, meriset tumpukan teknologi modern yang teruji di komunitas, dan menerapkan kaidah ML Best Practices.
* **Scope Pekerjaan:**
  - Melakukan audit menyeluruh terhadap [`Morrow_PRD_v0.2_Skill_Based.md`](../Morrow_PRD_v0.2_Skill_Based.md) dan 22 Kontrak Penerimaan (AC-001 s.d. AC-022).
  - Meriset dan menetapkan pustaka Python modern: `asyncio`, `Pydantic v2`, `aiosqlite (SQLite WAL)`, `DeepSeek (via modular interface)`, `PyMuPDF`, `openpyxl`, `python-docx`, `python-pptx`, `puremagic`, `Pillow`, `tenacity`, `aiogram v3`, dan `pytest`.
  - Menerapkan prinsip ML Best Practices (isolasi konteks tanpa kebocoran data, skema output JSON ketat, dataset tolok ukur evaluasi routing, dan pelaporan kegagalan jujur).
  - Menyusun dokumen artefak rencana kerja `implementation_plan.md` yang terbagi ke dalam 6 fase pengerjaan bertahap.
  - Memperbarui profil dan catatan observasi pengguna di [`user.md`](../user.md).
  - Menambahkan ADR-008 pada [`docs/DECISIONS.md`](../docs/DECISIONS.md).
* **File yang Berubah:**
  - `[NEW ARTIFACT]` `implementation_plan.md`
  - `[MODIFIED]` [`user.md`](../user.md)
  - `[MODIFIED]` [`docs/DECISIONS.md`](../docs/DECISIONS.md)
  - `[MODIFIED]` [`docs/WORKLOG.md`](../docs/WORKLOG.md)
* **Keputusan Penting:**
  - Tidak melakukan persetujuan otomatis (*no auto-approve*) sebelum mendapat konfirmasi eksplisit dari Mas Bima.
* **Next Action:**
  - Menunggu persetujuan Mas Bima untuk memulai eksekusi Tahap 1.

---

### [WL-002] Pengisian & Sinkronisasi Seluruh Dokumen dari PRD Morrow v0.2
* **Tanggal:** 2026-08-15
* **Tipe Pekerjaan:** Dokumentasi & Arsitektur
* **Status:** Completed
* **Tujuan:** Mengisi seluruh berkas dokumentasi di folder `docs/` dengan mengekstrak data resmi dari [`Morrow_PRD_v0.2_Skill_Based.md`](../Morrow_PRD_v0.2_Skill_Based.md).
* **Scope Pekerjaan:**
  - Mengisi [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md) dengan pembagian peran agen, peta kemampuan, dan batasan teknis (SQLite, DeepSeek, concurrency).
  - Mengisi [`docs/DECISIONS.md`](../docs/DECISIONS.md) dengan 7 keputusan arsitektur (ADR-001 s.d. ADR-007).
  - Mengisi [`docs/BUG_BACKLOG.md`](../docs/BUG_BACKLOG.md) dengan 6 catatan risiko keputusan terbuka (RSK-001 s.d. RSK-006 / OQ-001 s.d. OQ-006).
  - Mengisi [`docs/TESTING_GUIDE.md`](../docs/TESTING_GUIDE.md) dengan prosedur pengujian berbasis kontrak penerimaan (AC-001 s.d. AC-022).
  - Mengisi [`docs/RELEASE_NOTES.md`](../docs/RELEASE_NOTES.md) dengan ringkasan status rilis v0.2.0.
* **File yang Berubah:**
  - `[MODIFIED]` [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md)
  - `[MODIFIED]` [`docs/DECISIONS.md`](../docs/DECISIONS.md)
  - `[MODIFIED]` [`docs/BUG_BACKLOG.md`](../docs/BUG_BACKLOG.md)
  - `[MODIFIED]` [`docs/TESTING_GUIDE.md`](../docs/TESTING_GUIDE.md)
  - `[MODIFIED]` [`docs/RELEASE_NOTES.md`](../docs/RELEASE_NOTES.md)
  - `[MODIFIED]` [`docs/WORKLOG.md`](../docs/WORKLOG.md)
* **Keputusan Penting:**
  - Seluruh informasi disarikan murni dari dokumen PRD tanpa mengarang data fiktif.
* **Next Action:**
  - Menunggu keputusan dan arahan dari Mas Bima untuk langkah berikutnya.

---

### [WL-001] Inisiasi Struktur Folder Dokumentasi
* **Tanggal:** 2026-08-15
* **Tipe Pekerjaan:** Dokumentasi
* **Status:** Completed
* **Tujuan:** Menyiapkan struktur folder `docs/` dan subfolder `docs/archive/`.
* **File yang Dibuat:**
  - `[NEW]` [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md)
  - `[NEW]` [`docs/BUG_BACKLOG.md`](../docs/BUG_BACKLOG.md)
  - `[NEW]` [`docs/DECISIONS.md`](../docs/DECISIONS.md)
  - `[NEW]` [`docs/ERROR_SOLUTIONS.md`](../docs/ERROR_SOLUTIONS.md)
  - `[NEW]` [`docs/RELEASE_NOTES.md`](../docs/RELEASE_NOTES.md)
  - `[NEW]` [`docs/TESTING_GUIDE.md`](../docs/TESTING_GUIDE.md)
  - `[NEW]` [`docs/WORKLOG.md`](../docs/WORKLOG.md)
  - `[NEW]` [`docs/archive/README.md`](../docs/archive/README.md)
