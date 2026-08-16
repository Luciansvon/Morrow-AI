# 🤖 Morrow AI — Private Multi-Agent Executive Team

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Architecture](https://img.shields.io/badge/Architecture-1%20Backend%20%7C%203%20Telegram%20Bots-success.svg)](docs/ARCHITECTURE.md)
[![CI](https://img.shields.io/badge/CI-Python%203.11%20%2B%203.12-brightgreen.svg)](.github/workflows/chatgpt-full-fix.yml)
[![PRD](https://img.shields.io/badge/PRD-v0.2%20traceable-blueviolet.svg)](Morrow_PRD_v0.2_Skill_Based.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Morrow AI v0.2.4** adalah asisten tim multi-agent privat yang berjalan di satu backend dan tampil sebagai tiga bot Telegram independen: **Manager**, **Marketing**, dan **Advisor**. Setiap pesan memiliki satu primary owner sebelum delegasi, lalu Morrow memasang skill yang relevan, mengambil memori jangka panjang yang relevan, menyediakan tool yang aman, dan menjaga tindakan eksternal di balik approval eksplisit.

Tujuan pengalaman percakapannya bukan membuat user merasa sedang mengoperasikan dashboard chatbot. Morrow harus terasa seperti ngobrol dengan tiga rekan yang punya karakter, gaya humor, dan cara berpikir berbeda, tanpa berpura-pura benar-benar manusia ketika identitasnya ditanya langsung.

Morrow sengaja tidak dibangun sebagai satu chatbot yang sekadar berganti persona. **Role routing, persona, skill routing, tool capability, task ownership, memory scope, dan approval adalah lapisan yang berbeda.**

> **Source of truth:** PRD menjelaskan intent dan batas produk, tests/checks membuktikan konformansi, sedangkan code adalah implementation reality. Jika ketiganya berbeda, perbedaannya harus dilaporkan, bukan disamarkan.

---

## 🌟 Kapabilitas Utama

### 1. 🎭 Tiga Agent Independen + Persona Kultural

- **Manager**: koordinasi, prioritas, task/dependency, progress, dan delegasi. Persona kultural **Millennial Indonesia / early-internet native**.
- **Marketing**: campaign, positioning, market/customer insight, content, dan measurement. Persona kultural **Gen Z Indonesia / modern-internet native**.
- **Advisor**: decision analysis, risk, trade-off, scenario, dan recommendation. Persona **older Indonesian / Boomer-inspired cultural lens** tanpa menganggap semua orang tua sebagai stereotip yang sama.
- Semua role memakai satu orchestrator, task engine, approval gateway, storage, dan subsystem bersama tanpa mengubah identitas role masing-masing.

Persona bukan daftar slang. Setiap profile membawa pola komunikasi, humor, cultural memory, dan respons lintas-generasi. Dalam obrolan santai, agent boleh salah menangkap referensi generasi lain atau mengaitkannya dengan zamannya sendiri. Dalam pekerjaan serius, akurasi dan safety selalu mengalahkan gimmick persona.

Aturan percakapan natural yang berlaku untuk semua role:

- tidak membuka jawaban dengan disclaimer AI tanpa alasan;
- tidak menyebut nama role, tool, atau proses internal pada setiap balasan;
- pesan pendek boleh dibalas pendek;
- obrolan santai tidak dipaksa menjadi memo ber-heading;
- slang, emoji, meme, dan nostalgia tidak boleh di-spam;
- tidak mengarang pengalaman fisik atau masa lalu;
- jika ditanya langsung apakah manusia/bot/AI, agent menjawab jujur bahwa ia agent AI Morrow.

### 2. 🧩 Modular Skill System — 16 Skill

Skill dipilih **setelah role owner ditentukan**. Artinya skill memperluas kemampuan role, tetapi tidak pernah mengubah Manager menjadi Marketing atau Advisor hanya karena modelnya mampu menjawab.

| Role | Skill |
|---|---|
| Manager | `task_coordination`, `prioritization_triage`, `dependency_recovery`, `progress_review` |
| Marketing | `campaign_strategy`, `audience_positioning`, `market_research`, `content_strategy`, `marketing_measurement` |
| Advisor | `risk_decision_analysis`, `risk_premortem`, `scenario_planning`, `recommendation_synthesis` |
| Shared | `document_inspection`, `evidence_synthesis`, `assumption_audit` |

Katalog skill berada di [`skills/`](skills/). Setiap skill adalah artefak `SKILL.md` dengan frontmatter ringan seperti `name`, `description`, `eligible_roles`, `triggers`, serta metadata opsional `tools` dan `references`.

Router skill:

1. menerima role yang sudah dipilih oleh role router;
2. hanya mempertimbangkan skill yang eligible untuk role itu;
3. memberi ranking pada trigger yang cocok;
4. memasang maksimal **3 skill berbasis teks** per pesan agar context tetap bounded;
5. menambahkan `document_inspection` secara terpisah ketika ada attachment;
6. memakai core role skill sebagai fallback jika tidak ada trigger spesifik yang cocok.

Detail katalog dan aturan authoring ada di [`skills/README.md`](skills/README.md).

### 3. 🔎 Agent Tool Runtime & Browser Automation

Morrow menghubungkan agent runtime ke tool layer secara nyata. Tool dibagi berdasarkan siapa yang mengeksekusi dan apakah ada side effect.

| Capability | Implementasi | Approval |
|---|---|---|
| Web search | OpenRouter server tool `openrouter:web_search` | Tidak, read-only |
| Web fetch | OpenRouter server tool `openrouter:web_fetch` | Tidak, read-only |
| Current datetime | OpenRouter server tool `openrouter:datetime` | Tidak |
| Calculator | Local user-defined tool `calculate` dengan AST evaluator, tanpa `eval()` | Tidak |
| File/document inspection | Pipeline native parser/OCR/vision yang sudah ada | Tidak |
| Browser automation | Provider-neutral contract di `src/browser/` (`agent-browser`) | READ/PREPARE tidak; COMMIT wajib approval |
| Email/calendar/social/transaction | External-action tool policy | Wajib approval |

OpenRouter server tools dijalankan server-side dan model dapat memutuskan sendiri kapan perlu search/fetch/time. User-defined local tools memakai bounded tool loop di `AgentRuntime`, dieksekusi lewat `tool_executor`, dan tetap tunduk pada fail-closed `tool_policy`.

Browser automation menggunakan runtime `agent-browser` (Chromium-based) dengan isolasi *task-space* per sesi, fail-closed startup preflight, dan pemisahan pipa proses subprocess yang stabil di Windows/Linux/macOS.

11 browser capabilities diklasifikasikan secara ketat:

- **`READ`** (`browser_open`, `browser_snapshot`, `browser_screenshot`): membaca atau mengambil snapshot struktur halaman web tanpa mutasi eksternal (tidak memerlukan approval).
- **`PREPARE`** (`browser_fill`, `browser_type`, `browser_select`, `browser_check`, `browser_uncheck`, `browser_scroll`): memodifikasi state lokal formulir/halaman secara persisten dalam task-space terisolasi (tidak memerlukan approval).
- **`COMMIT`** (`browser_click`, `browser_press`): menekan tombol atau aksi pengiriman formulir yang dapat memicu side effect eksternal (**wajib melewati approval gateway**). Approval terikat sidik jari (*state hash*) halaman saat dibuat; jika isi formulir berubah sebelum persetujuan, approval lama otomatis digugurkan demi keamanan (*stale state invalidation*).

### 4. 🧠 Hybrid Long-Term Memory yang Hemat RAM

SQLite tetap menjadi **source of truth** untuk durable memory. Retrieval menggunakan kombinasi beberapa jalur yang fail-soft:

- **Pinned structured truth** untuk keputusan dan constraint penting.
- **FTS5 lexical retrieval** untuk kecocokan kata/frasa.
- **Semantic retrieval** dengan embedding + `sqlite-vec` bila tersedia.
- **Reciprocal Rank Fusion (RRF)** untuk menggabungkan lexical dan semantic candidates.
- **Role scope + shared scope** agar agent tidak menerima seluruh raw history role lain.
- **Memory audit** menyimpan provenance perubahan nilai.
- **Markdown mirror** di `data/memory/` untuk inspeksi manusia; SQLite tetap sumber kebenaran dan Morrow tidak bergantung pada Obsidian.

Jika semantic index atau Markdown mirror gagal, write ke durable structured memory tetap tidak boleh ikut gagal.

### 5. 🗣️ Routing, Social Chat, dan Multi-Agent Coordination

- Explicit role mention, reply-aware routing, known ownership, dan fast-path dipakai saat sinyalnya jelas.
- Ambiguous work tetap memilih **tepat satu primary owner** sebelum delegasi.
- Sapaan sederhana seperti `halo semua` tetap memakai zero-token fast path.
- Banter sosial yang lebih kaya seperti tawa, candaan, atau percakapan santai diarahkan ke persona-aware runtime dengan workload `casual`, sehingga agent tidak terdengar seperti template greeting statis.
- Agent-to-agent discussion dibatasi oleh loop guard agar percakapan otomatis tidak berubah menjadi rapat tanpa akhir, sebuah pencapaian yang bahkan manusia belum universal kuasai.

### 6. ⏳ Telegram Activity Preview

Saat agent membutuhkan reasoning/tool work, bot terkait menampilkan pesan sementara seperti:

- Manager: `bentar, lagi gue susun biar nggak muter-muter...`
- Marketing: `bentar, lagi gue cari angle yang paling kena...`
- Advisor: `sebentar, saya cek celahnya dulu...`

Adapter Telegram juga mengirim `typing` action bila tersedia. Activity message bersifat best-effort dan dihapus ketika pekerjaan selesai. Kegagalan menghapus activity **tidak boleh menggagalkan jawaban utama**.

### 7. 📁 File Intake Pra-Routing

Attachment diproses sebelum reasoning role-specific sehingga router dan agent mendapat konteks hasil ekstraksi, bukan sekadar nama file.

Format MVP: `PDF`, `DOCX`, `XLSX`, `CSV`, `TXT`, `MD`, `PPTX`, `PNG`, `JPG/JPEG`, dan `WEBP`.

Prinsipnya:

- structured formats memakai parser native jika struktur dapat dibaca;
- spreadsheet tidak di-OCR jika workbook dapat dibaca secara native;
- PDF dengan text layer memakai text extraction;
- scanned PDF dapat fallback ke render + OCR/vision;
- OCR dan visual understanding diperlakukan sebagai kemampuan berbeda;
- isi attachment selalu dianggap **untrusted input** dan tidak otomatis masuk durable memory.

### 8. 🛡️ Approval, Safety, dan Idempotensi

- Email/message eksternal, calendar mutation, posting sosial, transaksi, browser COMMIT, destructive external-data change, dan account modification memerlukan approval eksplisit yang scoped ke action tersebut.
- Parameter action difingerprint sehingga perubahan parameter tidak diam-diam memakai approval lama.
- Human-instruction conflict dapat menjeda task terkait dan meminta resolusi.
- Handoff chain mencegah task kembali ke agent yang sudah pernah dicoba.
- Duplicate delivery dan concurrency diperlakukan sebagai masalah state, bukan sesuatu yang diharapkan hilang karena keberuntungan.

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
                 ┌────────────────────┼────────────────────┐
                 ▼                    ▼                    ▼
          Access + Dedup        File Intake         Addressing/Intent
                 └────────────────────┼────────────────────┘
                                      ▼
                              System Orchestrator
                                      │
                              Primary Role Owner
                                      │
                   ┌──────────────────┼──────────────────┐
                   ▼                  ▼                  ▼
              Persona Layer       Skill Router       Activity UI
                   └──────────────────┼──────────────────┘
                                      ▼
            Manager Agent / Marketing Agent / Advisor Agent
                                      │
                         Bounded Agent Tool Loop
                                      │
              ┌───────────────────────┼───────────────────────┐
              ▼                       ▼                       ▼
      OpenRouter Server Tools    Local Internal Tools    External Tools
      search/fetch/datetime      calculator, future     approval required
              └───────────────────────┼───────────────────────┘
                                      ▼
        ┌────────────────────────────────────────────────────────┐
        │ Shared subsystems                                      │
        │ • Task engine + bounded handoff/retry                  │
        │ • Hybrid long-term memory: SQLite + FTS5 + sqlite-vec │
        │ • Markdown memory mirror                              │
        │ • Modular SKILL.md catalog                            │
        │ • Approval gateway + idempotent tool policy           │
        │ • Browser backend contract                            │
        │ • Conflict detector + loop guard                      │
        └────────────────────────────────────────────────────────┘
```

---

## 🧩 Menambah Skill Baru

Buat folder baru di `skills/<role-or-shared>/<skill-name>/SKILL.md`.

Contoh minimum:

```md
---
name: example_skill
description: Kapan dan untuk apa skill ini digunakan.
eligible_roles: [marketing]
triggers: [contoh trigger, istilah spesifik]
references: [references/checklist.md]
---
## Tujuan
Jelaskan outcome skill secara sempit dan terukur.

## Workflow
1. Gunakan fakta yang tersedia.
2. Bedakan fakta, asumsi, dan unknown bila relevan.
3. Jangan mengklaim side effect eksternal berhasil tanpa backend.

## Output
Definisikan bentuk output yang diharapkan.
```

Aturan desain utama:

- satu skill untuk satu workflow yang jelas;
- trigger harus cukup spesifik agar tidak menyalakan terlalu banyak skill;
- shared skill dipakai hanya untuk capability yang benar-benar lintas-role;
- skill tidak boleh melewati approval, role boundary, attachment trust boundary, atau backend guardrail;
- skill baru harus memiliki test eligibility/routing sebelum dianggap stabil.

---

## 🛠️ Menambah Tool Baru

Tool lokal didaftarkan ke `src/tools/registry.py` dengan JSON Schema parameter dan diklasifikasikan di `src/tools/policy.py`.

Prinsip wajib:

1. tool baru **tidak boleh dapat dieksekusi** sebelum masuk policy;
2. read-only/internal tool dapat dieksekusi langsung;
3. external side effect wajib melalui approval + idempotency;
4. jangan memberi LLM raw shell/code execution hanya karena mudah diimplementasikan;
5. tool loop dibatasi `MAX_TOOL_ROUNDS` agar agent tidak berputar tanpa akhir.

Server tools OpenRouter dapat dinyalakan/dimatikan melalui environment tanpa registrasi local executor.

---

## 🚀 Quickstart

### 1. Requirements

- Python 3.11+
- Git
- Node.js + npm (untuk PM2 process manager & runtime `agent-browser`)
- Google Chrome (untuk browser automation backend)

### 2. Clone & install

```powershell
git clone https://github.com/Luciansvon/Morrow-AI.git
cd Morrow-AI
python -m pip install -e ".[dev]"
npm install -g pm2 agent-browser
```

Install editable membuat command **`MORROW`** tersedia di terminal. Untuk runtime tanpa tool development, gunakan `python -m pip install -e .`.

### 3. Environment

```powershell
cp .env.example .env
```

Minimum setup:

```env
OPENROUTER_API_KEY=your_openrouter_api_key_here

WEB_SEARCH_ENABLED=true
WEB_FETCH_ENABLED=true
DATETIME_TOOL_ENABLED=true
MORROW_TIMEZONE=Asia/Jakarta

# Browser Automation (agent-browser)
BROWSER_ENABLED=true
BROWSER_BACKEND=agent-browser
BROWSER_AGENT_EXECUTABLE=agent-browser

TELEGRAM_MANAGER_BOT_TOKEN=your_manager_bot_token
TELEGRAM_MARKETING_BOT_TOKEN=your_marketing_bot_token
TELEGRAM_ADVISOR_BOT_TOKEN=your_advisor_bot_token

TELEGRAM_ALLOWED_GROUP_IDS=-100xxxxxxxxxx
TELEGRAM_WHITELIST_USER_IDS=xxxxxxxxx

DATABASE_PATH=./data/morrow.db
STORAGE_DIR=./data/storage
MEMORY_VAULT_DIR=./data/memory
MEMORY_SEMANTIC_ENABLED=true
MEMORY_HYBRID_TOP_K=8
```

Web search/fetch memakai OpenRouter server tools sehingga **tidak memerlukan API key search provider tambahan**. Konfigurasi result cap, context size, fetch token limit, tool rounds, embedding memory, timeout, model routing, dan limit lainnya tersedia di `.env.example` / `src/core/config.py`.

### 4. BotFather

Untuk ketiga bot:

- `/setjoingroups` → **Enable**
- `/setprivacy` → **Disable** agar bot dapat membaca pesan grup yang diperlukan
- masukkan ketiga bot ke grup yang sudah di-allowlist

### 5. Test

```powershell
ruff check .
pytest -q
```

CI menjalankan Ruff + pytest pada Python **3.11 dan 3.12**.

### 6. Run dengan satu command

```powershell
MORROW
```

Tanpa subcommand, `MORROW` akan start Morrow melalui PM2. Jika proses `morrow` sudah terdaftar, command yang sama akan melakukan restart dengan environment terbaru. Setelah start/restart berhasil, launcher menjalankan `pm2 save`, sehingga daftar proses tersimpan untuk proses resurrection/startup.

PM2 menjalankan hanya **1 instance** Morrow, mematikan file watch, dan memakai exponential restart backoff. Jika polling Telegram gagal sampai runtime keluar, PM2 akan menyalakan proses lagi. Terminal yang dipakai untuk menjalankan `MORROW` boleh ditutup setelah proses aktif.

Command kontrol:

| Command | Fungsi |
|---|---|
| `MORROW` | Start atau restart Morrow lewat PM2, lalu save process list |
| `MORROW status` | Lihat status proses Morrow |
| `MORROW logs` | Streaming log PM2 untuk Morrow |
| `MORROW restart` | Restart manual + update environment |
| `MORROW stop` | Stop proses dan simpan state PM2 |
| `MORROW delete` | Hapus proses dari PM2 dan simpan process list baru |
| `MORROW foreground` | Jalankan langsung tanpa PM2 untuk debugging |
| `MORROW startup` | Siapkan proses agar dapat dipulihkan setelah reboot/sign-in |

#### Startup setelah reboot

**Windows:** `MORROW startup` membuat Windows Scheduled Task untuk user saat ini. Task menjalankan `pm2 resurrect` setelah user sign-in, memakai process list yang sudah disimpan oleh PM2.

**Linux/macOS:** `MORROW startup` menjalankan `pm2 startup`. PM2 dapat mencetak satu command privileged/sudo yang harus dijalankan sekali sesuai init system mesin tersebut. Process list Morrow sudah disimpan oleh launcher.

Startup normal menginisialisasi database serta long-term memory indexes/mirror sebelum adapter Telegram mulai menerima pesan.

---

## 💬 Contoh

| Pesan | Owner / Capability |
|---|---|
| `halo semua` | zero-token social broadcast, masing-masing role punya gaya sendiri |
| `Manager, wkwk lu kocak` | Manager persona runtime dalam mode casual |
| `Manager, prioritaskan backlog ini` | Manager + `prioritization_triage` |
| `Marketing, cari tren campaign terbaru` | Marketing + `market_research` + web search bila model menilai perlu |
| `Manager, buka https://example.com lalu rangkum isinya` | Manager + live browser automation (`agent-browser` READ) |
| `cek isi URL ini` | web fetch bila URL perlu dibaca langsung |
| `hitung (12500 * 3) + 4500` | local calculator tool |
| `Advisor, buat pre-mortem rencana ini` | Advisor + `risk_premortem` |
| `cek asumsi di dokumen ini` + PDF | Role owner + `document_inspection` + `assumption_audit` bila trigger cocok |
| `semua, bantu strategi launch` | bounded multi-agent collaboration dengan coordinator |
| `/approve appr_12345` | approval gateway untuk action eksternal / browser COMMIT yang diajukan |

---

## 📂 Struktur Repositori

```text
Morrow-AI/
├── ecosystem.config.cjs       # PM2 keep-alive / restart policy
├── scripts/
│   └── install_pm2_startup.ps1 # Windows startup via Scheduled Task
├── skills/                    # Katalog 16 modular SKILL.md
│   ├── manager/
│   ├── marketing/
│   ├── advisor/
│   └── shared/
├── docs/                      # Architecture, decisions, testing, worklog, backlog
├── src/
│   ├── adapters/              # Telegram multi-bot + CLI + activity lifecycle
│   ├── agents/                # Independent role runtimes + bounded tool loop
│   ├── approval/              # Scoped external-action approval
│   ├── browser/               # Provider-neutral browser automation contract
│   ├── core/                  # Orchestrator, config, shared types
│   ├── files/                 # Native parsers, OCR, vision pipeline
│   ├── launcher.py            # MORROW command + PM2 process controls
│   ├── llm/                   # Provider client, policy, usage metering
│   ├── memory/                # Hybrid retrieval, vector index, Markdown vault, judge
│   ├── persona/               # Generational/cultural persona profiles
│   ├── routing/               # Addressing, intent, role routing, social fast path
│   ├── safety/                # Conflict detector + loop guard
│   ├── skills/                # SKILL.md loader, registry, router
│   ├── storage/               # SQLite schema/driver + attachments
│   ├── tasks/                 # Task lifecycle + handoff
│   └── tools/                 # Registry, schemas, builtins, server tools, policy/executor
├── tests/                     # Unit, integration, regression, hardening
├── Morrow_PRD_v0.2_Skill_Based.md
├── pyproject.toml
└── requirements.txt
```

---

## 📜 License

Morrow AI dilisensikan di bawah [MIT License](LICENSE).
