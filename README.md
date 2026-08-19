# 🤖 Morrow AI — Private Multi-Agent Executive Team

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Stable](https://img.shields.io/badge/stable-v0.2.6-success.svg)](docs/RELEASE_NOTES.md)
[![v0.3](https://img.shields.io/badge/v0.3-feature--flagged-orange.svg)](AGENTS.md)
[![Architecture](https://img.shields.io/badge/architecture-one%20backend%20%7C%203%20Telegram%20roles-blueviolet.svg)](docs/ARCHITECTURE.md)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

**Morrow AI v0.2.6** adalah sistem asisten multi-agent privat yang menjalankan tiga role AI tetap dalam satu backend: **Manager**, **Marketing**, dan **Advisor**. Telegram adalah transport utama saat ini, bukan batas arsitektur. User dapat bicara langsung ke satu role, beberapa role, atau seluruh tim; untuk pesan biasa tanpa target eksplisit, Morrow memilih satu primary owner agar grup tidak berubah menjadi rapat yang semua pesertanya bicara bersamaan.

Morrow memisahkan **role authority, persona, skill routing, tool capability, task ownership, memory scope, approval, dan integration layer**. Model boleh pintar. Model tetap tidak diberi izin untuk mengarang otoritasnya sendiri. Sebuah standar yang, tragisnya, juga cukup berguna di organisasi manusia.

> **Source of truth:** `AGENTS.md` + PRD/decision docs menjelaskan intent dan invariants, tests/checks membuktikan conformance, dan code adalah implementation reality. README ini hanya mengiklankan capability yang sudah ada atau secara eksplisit diberi label experimental/planned.

---

## 📌 Status Saat Ini

| Area | Status | Keterangan |
|---|---|---|
| Core runtime | ✅ Stable baseline | **v0.2.6** |
| Durable roles | ✅ Aktif | Manager, Marketing, Advisor |
| Direct role targeting | ✅ Aktif | User dapat mention satu atau beberapa role secara langsung |
| Collective routing | ✅ Aktif | Mendukung `@semua`, bentuk natural seperti `semua ...`, dan multi-role addressing |
| Telegram reply continuity | ✅ Aktif | Reply chain membawa role/thread/root-request context |
| Reliable Action Layer | ✅ Aktif | Progressive tool discovery, journal, approval, idempotency, provenance |
| Browser automation | ✅ Aktif, opt-in | `agent-browser` default production backend |
| Hybrid memory | ✅ Aktif | SQLite + FTS5 + optional `sqlite-vec` + Markdown mirror |
| User-private memory boundary | ✅ Aktif | User memory dibedakan dari shared group memory |
| OpenViking adapter | 🧪 Experimental | Feature-flagged, default OFF |
| Immich adapter | 🧪 Experimental | Feature-flagged, default OFF |
| v0.3 orchestrator path | 🧪 Migration boundary | Default OFF; v0.2.6 path tetap authoritative |
| Maintenance agent | 🗺️ Belum runtime | Belum menjadi durable role pada source saat ini |
| Temporal | ⏸️ Deferred | Tidak masuk scope migrasi saat ini |

---

## 👥 Tiga Role Morrow

### Manager — Pragmatic Action Manager

- Domain: koordinasi, prioritas, task ownership, blocker, delegasi, dan next action.
- Persona behavioral: **Bob Sadino-inspired**, tanpa impersonation.
- Default lens: *Apa keputusan dan apa yang kita kerjakan berikutnya?*
- Framework: `Problem → Simplify → Decide → Assign → Execute → Observe → Adjust`.
- Jika Manager ikut dalam kerja multi-agent, Manager memegang coordination authority. Authority ini tetap berada di bawah user, permission, safety, dan approval policy.

### Marketing — Technical Growth Strategist

- Domain: audience, positioning, market/customer insight, campaign, content, experiment, dan measurement.
- Persona behavioral: **Dharmesh Shah-inspired**, tanpa impersonation.
- Default lens: *Bagaimana kita tahu ini benar dan bagaimana mengujinya?*
- Framework: `Audience → Problem → Insight → Hypothesis → Experiment → Metric → Learning`.
- Fokus pada evidence dan eksperimen, bukan hype atau vanity metric.

### Advisor — Visionary Humanist Advisor

- Domain: decision analysis, scenario, risk, trade-off, blind spot, people/customer impact, dan arah jangka panjang.
- Persona behavioral: **Jack Ma-inspired**, tanpa impersonation.
- Default lens: *Ke mana keputusan ini membawa customer, people, trust, dan arah jangka panjang?*
- Framework: `Purpose → People → Future → Opportunity → Risk → Perspective → Advice`.
- Advisor dapat menantang arah dan memberi alternatif, tetapi tidak mengambil alih keputusan operasional Manager.

Persona adalah behavioral contract, bukan cosplay. Pada pekerjaan serius atau berisiko tinggi, akurasi, evidence, dan safety mengalahkan humor atau gaya karakter.

---

## 🧭 Routing & Multi-Agent Coordination

Morrow tidak memakai aturan “semua pesan harus lewat Manager”. Routing saat ini mendukung direct specialist targeting dan collective addressing.

### Direct targeting

Contoh:

```text
Marketing, cek positioning produk ini.
Advisor, pre-mortem rencana ekspansi ini.
Manager, prioritaskan backlog minggu ini.
Manager dan Marketing, cek launch ini.
```

Jika role disebut secara eksplisit sebagai target, Morrow menghormati target tersebut. Bare role words yang hanya menjadi objek kalimat tidak otomatis dianggap addressing, sehingga kalimat seperti `apa bedanya manager dan advisor` tidak berubah menjadi fan-out tanpa alasan.

### Collective targeting

Contoh:

```text
@semua analisis ini.
semua tolong cek rencana launch.
terimakasih semua
```

Morrow membedakan collective addressing dari object quantifier. `cek semua produk` berarti cek seluruh produk, bukan panggil seluruh agent. Karena ternyata kata “semua” memang mampu menciptakan lebih banyak masalah routing daripada yang selayaknya dilakukan satu kata.

### Default owner

Untuk request biasa tanpa target eksplisit, semantic routing memilih **satu primary owner**. Jika task analysis membutuhkan collaborator tambahan, Morrow dapat menjalankan collaboration flow secara bounded.

### Durable collective completion

Kerja multi-agent memakai per-agent execution ledger. Task tidak boleh ditandai `done` hanya karena satu agent menjawab. Jika target wajib gagal, task tetap `blocked`/belum lengkap dan contributor lain tetap dapat dicoba.

Current stable v0.2 path tidak diiklankan sebagai unrestricted parallel swarm. Concurrency yang lebih agresif adalah bagian dari arah migrasi v0.3 dan harus tetap tunduk pada ownership, budget, loop guard, approval, dan evidence.

---

## 🎭 Natural Telegram Behavior

Morrow memakai paragraph-first response contract agar jawaban tidak otomatis berubah menjadi laporan korporat penuh heading, bold, dan checklist setiap kali user hanya bertanya satu kalimat.

Aturan umum:

- pesan pendek boleh dibalas pendek;
- heading/list hanya dipakai saat benar-benar membantu;
- agent tidak mengulang isi gambar/file secara panjang sebelum menganalisis;
- role/tool/routing internal tidak diumumkan tanpa kebutuhan;
- agent tidak mengarang pengalaman pribadi atau mengaku sebagai tokoh inspirasinya;
- jika ditanya apakah manusia/bot/AI, agent menjawab jujur bahwa ia agent AI Morrow;
- serious/high-risk context menekan humor dan gimmick persona.

Telegram activity preview dan `typing` action digunakan secara best-effort saat reasoning/tool work berjalan. Kegagalan activity UI tidak boleh menggagalkan jawaban utama.

---

## 🧩 Modular Skill System

Skill dipilih **setelah role owner ditentukan**. Skill memperluas kemampuan role, tetapi tidak mengubah authority role.

| Role | Core skills |
|---|---|
| Manager | `task_coordination`, `prioritization_triage`, `dependency_recovery`, `progress_review` |
| Marketing | `campaign_strategy`, `audience_positioning`, `market_research`, `content_strategy`, `marketing_measurement` |
| Advisor | `risk_decision_analysis`, `risk_premortem`, `scenario_planning`, `recommendation_synthesis` |
| Shared | `document_inspection`, `evidence_synthesis`, `assumption_audit` |

Katalog berada di [`skills/`](skills/). Setiap skill menggunakan `SKILL.md` dengan metadata seperti `name`, `description`, `eligible_roles`, `triggers`, serta references/tool requirements bila memang tersedia di runtime.

Skill tidak boleh mengiklankan tool backend yang tidak benar-benar terdaftar. Tool discovery adalah exposure capability, bukan permission.

---

## 🛠️ Tool Runtime & Reliable Action Layer

Morrow memiliki bounded tool loop, progressive discovery, execution journal, schema validation, provenance, dan fail-closed policy.

| Capability | Implementasi | Approval |
|---|---|---|
| Web search | OpenRouter server tool | Tidak, read-only |
| Web fetch | OpenRouter server tool | Tidak, read-only |
| Current datetime | Local deterministic tool / configured timezone | Tidak |
| Calculator | Local AST evaluator | Tidak |
| File/document inspection | Native parser + OCR/vision pipeline | Tidak |
| Browser READ | `agent-browser`: open/snapshot/screenshot | Tidak |
| Browser PREPARE | fill/type/select/check/uncheck/scroll | Tidak |
| Browser COMMIT | click/press yang dapat memicu side effect | **Wajib approval** |
| External actions | email/calendar/social/transaction dan capability sejenis | **Wajib approval** |

### Guardrails tool

- unknown/unclassified tool gagal secara fail-closed;
- public JSON Schema divalidasi lagi di executor boundary sebelum function dipanggil;
- progressive discovery membatasi schema yang diekspos ke model;
- execution journal menyimpan policy decision, status, provenance, approval link, side-effect flag, dan retry safety;
- external/COMMIT action tidak dieksekusi hanya karena model mengeluarkan tool call;
- approval exact-bound ke parameter/state dan one-shot;
- browser COMMIT juga terikat page/form state fingerprint;
- outcome eksternal yang `unknown` tidak di-retry otomatis.

---

## 🌐 Browser Automation

Backend produksi default adalah **`agent-browser`**, tetap opt-in melalui `BROWSER_ENABLED`.

Morrow mempertahankan pemisahan tiga kelas aksi:

1. **READ** — membaca halaman tanpa mutasi eksternal.
2. **PREPARE** — menyiapkan state form/page dalam isolated task-space.
3. **COMMIT** — aksi yang dapat memicu side effect dan wajib approval.

Task-space browser diisolasi per pekerjaan. Model tidak dapat memilih internal task-space sesuka hati. Browser intent juga tidak boleh diam-diam disubstitusi menjadi simple `web_fetch` lalu diklaim sebagai browser interaktif.

---

## 🧠 Hybrid Long-Term Memory

SQLite tetap menjadi authoritative local source pada baseline v0.2.6.

Retrieval menggabungkan:

- structured durable memory;
- FTS5 lexical search;
- semantic retrieval dengan embeddings + `sqlite-vec` bila tersedia;
- Reciprocal Rank Fusion untuk menggabungkan candidate;
- relevance gating untuk mengurangi memory contamination;
- Markdown mirror untuk inspeksi manusia.

### Memory scopes

- **USER** — private memory per user di dalam group boundary.
- **ROLE** — memory yang scoped ke role.
- **SHARED** — keputusan/fakta/status yang memang layak dibagi dalam group.

Explicit save harus benar-benar durable sebelum agent mengakui bahwa informasi sudah tersimpan. Assistant speculation, external claims yang belum terverifikasi, dan angka yang hanya muncul dari jawaban model tidak boleh otomatis menjadi durable user memory.

---

## 📁 File Intake Pra-Routing

Attachment diproses sebelum role reasoning sehingga router mendapat konteks isi file, bukan cuma nama file.

Format MVP:

`PDF`, `DOCX`, `XLSX`, `CSV`, `TXT`, `MD`, `PPTX`, `PNG`, `JPG/JPEG`, `WEBP`.

Prinsip utama:

- structured format memakai parser native jika memungkinkan;
- spreadsheet tidak di-OCR jika workbook dapat dibaca langsung;
- PDF text-layer memakai text extraction;
- scanned PDF dapat fallback ke render + OCR/vision;
- OCR dan visual understanding diperlakukan sebagai capability berbeda;
- file content adalah untrusted input dan tidak otomatis masuk durable memory;
- resource caps membatasi ukuran attachment, jumlah halaman OCR, archive expansion, spreadsheet rows/cells, image pixels, dan extracted context.

---

## 🛡️ Task, Event, Approval & Concurrency Safety

Hardening v0.2.6 + audit fixes menambahkan boundary yang lebih ketat untuk state yang mudah rusak saat concurrency, crash, atau duplicate delivery muncul.

- `processed_events` menggunakan durable ownership/lease dengan owner token sehingga stale worker tidak boleh menyelesaikan attempt milik worker baru;
- task dependency benar-benar memblokir start sebelum dependency selesai;
- terminal task tidak boleh dibuka kembali melalui unconditional status update;
- task model memakai persisted timestamps dari database;
- pause/cancel menahan stale in-flight completion melalui generation/ownership boundary dan membatalkan agent run yang relevan;
- collective task memakai durable `task_agent_runs` untuk tracking per target;
- approval execution memiliki lease/recovery behavior sehingga crash tidak memicu blind replay side effect;
- control intent seperti `stop`, `batal`, `jangan lanjut`, pause, dan resume diperlakukan berbeda dari work prompt biasa.

---

## 🧪 v0.3 Migration Boundary

Repo saat ini sudah menyiapkan integration boundary v0.3, tetapi **default tetap v0.2.6**.

```env
MORROW_V03_ORCHESTRATOR_ENABLED=false
OPENVIKING_ENABLED=false
IMMICH_ENABLED=false
```

### OpenViking

Adapter berada di `src/integrations/openviking.py` dan diposisikan untuk context/memory/knowledge/skills/experience infrastructure.

Prinsip:

- feature-flagged;
- scoped account/user headers;
- tidak menjadi approval authority;
- tidak menggantikan role authority Morrow Core;
- saat disabled, adapter fail closed;
- migrasi tidak boleh menciptakan dua semantic-memory authority tanpa kontrak yang jelas.

### Immich

Adapter berada di `src/integrations/immich.py` dan diposisikan untuk media asset search/index/metadata.

Prinsip:

- media binary tetap milik Immich;
- Immich bukan general conversational memory;
- ownership scope tidak boleh dikontrol bebas oleh caller/model;
- API key untuk adapter saat ini sebaiknya read-only;
- saat disabled, adapter fail closed atau runtime tetap memakai local attachment path sesuai capability yang diminta.

### Orchestration direction

Arah v0.3 menempatkan orchestration framework sebagai **execution layer**, bukan product brain. Morrow Core tetap authoritative untuk permission, routing semantics, role authority, task behavior, approval, external-action authority, dan safety invariants.

Microsoft Agent Framework adalah arah orchestrator yang dipilih pada migration contract, tetapi bukan alasan untuk mengganti seluruh Morrow Core sekaligus. Existing v0.2.6 path wajib tetap bekerja saat feature flag OFF.

**Temporal masih deferred.** Jangan ditambahkan hanya karena diagram arsitektur terasa kurang ramai.

---

## 🏛️ Arsitektur Ringkas

```text
                         Private Telegram Group
            ┌────────────────┬────────────────┬────────────────┐
            │  Manager Bot   │ Marketing Bot  │  Advisor Bot   │
            └────────┬───────┴───────┬────────┴───────┬────────┘
                     └───────────────┼────────────────┘
                                     ▼
                          ONE MORROW BACKEND
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        ▼                            ▼                            ▼
 Access + Event Lease         File Intake                Addressing/Intent
        └────────────────────────────┼────────────────────────────┘
                                     ▼
                           System Orchestrator
                                     │
                         Primary Owner / Coordinator
                                     │
              ┌──────────────────────┼──────────────────────┐
              ▼                      ▼                      ▼
        Persona Layer           Skill Router          Task / Run Ledger
              └──────────────────────┼──────────────────────┘
                                     ▼
                     Bounded Agent + Tool Runtime
                                     │
          ┌──────────────────────────┼──────────────────────────┐
          ▼                          ▼                          ▼
 OpenRouter Server Tools      Local/Internal Tools      External / COMMIT
 search/fetch                 calculator/browser       approval required
          └──────────────────────────┼──────────────────────────┘
                                     ▼
 ┌────────────────────────────────────────────────────────────────────┐
 │ Shared subsystems                                                  │
 │ • SQLite task/event/approval/tool journal                         │
 │ • USER / ROLE / SHARED hybrid memory                             │
 │ • FTS5 + optional sqlite-vec + Markdown mirror                   │
 │ • Modular SKILL.md catalog                                      │
 │ • Conflict detector + loop guard + usage budget                 │
 │ • Feature-flagged OpenViking / Immich integration adapters      │
 └────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quickstart

### Requirements

- Python 3.11+
- Git
- Node.js + npm
- Google Chrome / Chromium-compatible runtime untuk browser automation
- 3 Telegram bot tokens jika menjalankan semua durable role

### Clone & install

```powershell
git clone https://github.com/Luciansvon/Morrow-AI.git
cd Morrow-AI
python -m pip install -e ".[dev]"
npm install -g pm2 agent-browser
agent-browser install
```

Install editable membuat command **`MORROW`** tersedia di terminal. Untuk runtime tanpa dev dependencies:

```powershell
python -m pip install -e .
```

### Environment

```powershell
cp .env.example .env
```

Minimum baseline:

```env
OPENROUTER_API_KEY=your_openrouter_api_key_here
MORROW_TIMEZONE=Asia/Jakarta

TELEGRAM_MANAGER_BOT_TOKEN=your_manager_bot_token
TELEGRAM_MARKETING_BOT_TOKEN=your_marketing_bot_token
TELEGRAM_ADVISOR_BOT_TOKEN=your_advisor_bot_token
TELEGRAM_ALLOWED_GROUP_IDS=-100xxxxxxxxxx
TELEGRAM_WHITELIST_USER_IDS=xxxxxxxxx

DATABASE_PATH=./data/morrow.db
STORAGE_DIR=./data/storage
MEMORY_VAULT_DIR=./data/memory
```

Optional browser:

```env
BROWSER_ENABLED=true
BROWSER_BACKEND=agent-browser
BROWSER_AGENT_EXECUTABLE=agent-browser
```

Experimental integrations sebaiknya tetap OFF sampai service dan scope access benar-benar disiapkan:

```env
MORROW_V03_ORCHESTRATOR_ENABLED=false
OPENVIKING_ENABLED=false
IMMICH_ENABLED=false
```

Lihat [`.env.example`](.env.example) untuk seluruh timeout, budget, attachment cap, memory, browser, OpenViking, Immich, dan tool-discovery settings.

### BotFather

Untuk ketiga bot:

- `/setjoingroups` → **Enable**
- `/setprivacy` → **Disable** jika bot perlu membaca message group yang bukan direct command/reply
- tambahkan bot ke group yang sudah di-allowlist

### Validation

```powershell
ruff check .
python -m compileall -q src scripts morrow_runtime.py
pytest -q
git diff --check
```

CI saat ini menambah compile verification, whitespace/diff check, deterministic audit acceptance tests, full pytest pada Python 3.11/3.12, dan verified-source packaging gate. Release staging juga menolak packaging yang membawa local `.env`.

### Run

```powershell
MORROW
```

Tanpa subcommand, launcher start/restart Morrow melalui PM2 dan menyimpan process list.

| Command | Fungsi |
|---|---|
| `MORROW` | Start/restart lewat PM2 |
| `MORROW status` | Lihat status proses |
| `MORROW logs` | Streaming log |
| `MORROW restart` | Restart + refresh environment |
| `MORROW stop` | Stop process |
| `MORROW delete` | Hapus process dari PM2 |
| `MORROW foreground` | Jalankan tanpa PM2 untuk debugging |
| `MORROW startup` | Siapkan resurrection/startup setelah reboot/sign-in |

---

## 💬 Contoh Perilaku

| Pesan | Hasil yang diharapkan |
|---|---|
| `halo semua` | collective social response dengan role persona masing-masing |
| `Marketing, cari angle launch produk ini` | direct Marketing ownership |
| `Advisor, cek blind spot keputusan ini` | direct Advisor ownership |
| `Manager, prioritaskan backlog ini` | direct Manager ownership |
| `Manager dan Marketing, cek launch ini` | multi-role collaboration; Manager coordinator |
| `@semua analisis toko Etsy minggu ini` | collective routing ke seluruh durable roles |
| `cek semua produk` | **bukan** collective addressing; “semua” adalah object quantifier |
| `Manager, buka https://example.com dan inspect` | browser READ path bila browser enabled |
| `isi form ini` | browser PREPARE; belum commit eksternal |
| `klik submit` | browser COMMIT; wajib approval |
| `catat sebagai keputusan: gunakan veneer walnut` | durable memory write sebelum acknowledgement |
| `stop` / `batal` | control path, bukan ordinary work prompt |

---

## 📂 Struktur Repositori

```text
Morrow-AI/
├── AGENTS.md                   # Repository-wide invariants & migration contract
├── ecosystem.config.cjs       # PM2 keep-alive / restart policy
├── Morrow_PRD_v0.2_Skill_Based.md
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DECISIONS.md
│   ├── RELEASE_NOTES.md
│   ├── AUDIT_2026-08-19.md
│   ├── BUG_BACKLOG.md
│   └── TESTING_GUIDE.md
├── scripts/                    # Setup, validation, release, acceptance helpers
├── skills/
│   ├── manager/
│   ├── marketing/
│   ├── advisor/
│   └── shared/
├── src/
│   ├── adapters/               # Telegram / channel adapters
│   ├── agents/                 # Role runtimes
│   ├── approval/               # Approval + recovery boundary
│   ├── browser/                # Provider-neutral browser layer
│   ├── core/                   # Orchestrator, config, shared types
│   ├── files/                  # Native parsing, OCR, vision
│   ├── integrations/           # OpenViking + Immich feature-flagged adapters
│   ├── llm/                    # OpenRouter client, model policy, usage budget
│   ├── memory/                 # Hybrid memory, user scope, vector/mirror
│   ├── persona/                # Versioned behavioral persona contracts
│   ├── routing/                # Addressing, intent, role routing, social fast path
│   ├── safety/                 # Conflict detector + loop guard
│   ├── skills/                 # Skill registry/router
│   ├── storage/                # SQLite schema/driver + attachment storage
│   ├── tasks/                  # Task lifecycle, dependencies, per-agent runs
│   └── tools/                  # Registry, discovery, schema validation, executor
├── tests/                      # Unit, integration, audit/regression coverage
├── pyproject.toml
└── requirements.txt
```

---

## 🧭 Dokumentasi Penting

- [`AGENTS.md`](AGENTS.md) — invariants dan migration boundary terbaru untuk coding agents.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — arsitektur implementasi.
- [`docs/DECISIONS.md`](docs/DECISIONS.md) — ADR dan keputusan desain.
- [`docs/RELEASE_NOTES.md`](docs/RELEASE_NOTES.md) — riwayat release v0.2.x.
- [`docs/AUDIT_2026-08-19.md`](docs/AUDIT_2026-08-19.md) — audit baseline yang memicu hardening terbaru.
- [`docs/TESTING_GUIDE.md`](docs/TESTING_GUIDE.md) — cara menjalankan validation/acceptance checks.

---

## 🚧 Batasan yang Sengaja Tidak Disamarkan

- Runtime durable saat ini masih **3 role**. Maintenance belum menjadi agent aktif di source.
- OpenViking dan Immich sudah memiliki adapter boundary, tetapi default **OFF** dan belum menggantikan local v0.2.6 path.
- v0.3 orchestrator migration masih feature-flagged; tidak ada flag-day rewrite.
- Temporal belum menjadi dependency/runtime requirement.
- External side effects tetap membutuhkan approval, meskipun connector/tool secara teknis tersedia.
- Passing unit tests tidak otomatis berarti live Telegram/browser/provider acceptance sudah terbukti di semua environment.

---

## 📜 License

Morrow AI dilisensikan di bawah [MIT License](LICENSE).
