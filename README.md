# 🤖 Morrow AI — Private Multi-Agent Executive Team

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Architecture](https://img.shields.io/badge/Architecture-1%20Backend%20%7C%203%20Telegram%20Bots-success.svg)](docs/ARCHITECTURE.md)
[![CI](https://img.shields.io/badge/CI-Python%203.11%20%2B%203.12-brightgreen.svg)](.github/workflows/chatgpt-full-fix.yml)
[![PRD](https://img.shields.io/badge/PRD-v0.2%20traceable-blueviolet.svg)](Morrow_PRD_v0.2_Skill_Based.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Morrow AI v0.2.3** adalah asisten tim multi-agent privat yang berjalan di satu backend dan tampil sebagai tiga bot Telegram independen: **Manager**, **Marketing**, dan **Advisor**. Setiap pesan memiliki satu primary owner sebelum delegasi, lalu Morrow memasang skill yang relevan untuk role tersebut, mengambil memori jangka panjang yang relevan, dan menjaga tindakan eksternal di balik approval eksplisit.

Morrow sengaja tidak dibangun sebagai satu chatbot yang sekadar berganti persona. Role routing, skill routing, task ownership, memory scope, dan approval adalah lapisan yang berbeda.

> **Source of truth:** PRD menjelaskan intent dan batas produk, tests/checks membuktikan konformansi, sedangkan code adalah implementation reality. Jika ketiganya berbeda, perbedaannya harus dilaporkan, bukan disamarkan.

---

## 🌟 Kapabilitas Utama

### 1. 🎭 Tiga Agent Independen, Satu Backend

- **Manager**: koordinasi, prioritas, task/dependency, progress, dan delegasi.
- **Marketing**: campaign, positioning, market/customer insight, content, dan measurement.
- **Advisor**: decision analysis, risk, trade-off, scenario, dan recommendation.
- Semua role memakai satu orchestrator, task engine, approval gateway, storage, dan subsystem bersama tanpa mengubah identitas role masing-masing.

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

### 3. 🧠 Hybrid Long-Term Memory yang Hemat RAM

SQLite tetap menjadi **source of truth** untuk durable memory. Retrieval menggunakan kombinasi beberapa jalur yang fail-soft:

- **Pinned structured truth** untuk keputusan dan constraint penting.
- **FTS5 lexical retrieval** untuk kecocokan kata/frasa.
- **Semantic retrieval** dengan embedding + `sqlite-vec` bila tersedia.
- **Reciprocal Rank Fusion (RRF)** untuk menggabungkan lexical dan semantic candidates.
- **Role scope + shared scope** agar agent tidak menerima seluruh raw history role lain.
- **Memory audit** menyimpan provenance perubahan nilai.
- **Markdown mirror** di `data/memory/` untuk inspeksi manusia; SQLite tetap sumber kebenaran dan Morrow tidak bergantung pada Obsidian.

Jika semantic index atau Markdown mirror gagal, write ke durable structured memory tetap tidak boleh ikut gagal.

### 4. 🗣️ Routing & Multi-Agent Coordination

- Explicit role mention, reply-aware routing, known ownership, dan fast-path dipakai saat sinyalnya jelas.
- Ambiguous work tetap memilih **tepat satu primary owner** sebelum delegasi.
- Social broadcast dan bounded multi-agent discussion dipisahkan dari work routing biasa.
- Agent-to-agent discussion dibatasi oleh loop guard agar percakapan otomatis tidak berubah menjadi rapat tanpa akhir, sebuah pencapaian yang bahkan manusia belum universal kuasai.

### 5. 📁 File Intake Pra-Routing

Attachment diproses sebelum reasoning role-specific sehingga router dan agent mendapat konteks hasil ekstraksi, bukan sekadar nama file.

Format MVP: `PDF`, `DOCX`, `XLSX`, `CSV`, `TXT`, `MD`, `PPTX`, `PNG`, `JPG/JPEG`, dan `WEBP`.

Prinsipnya:

- structured formats memakai parser native jika struktur dapat dibaca;
- spreadsheet tidak di-OCR jika workbook dapat dibaca secara native;
- PDF dengan text layer memakai text extraction;
- scanned PDF dapat fallback ke render + OCR/vision;
- OCR dan visual understanding diperlakukan sebagai kemampuan berbeda;
- isi attachment selalu dianggap **untrusted input** dan tidak otomatis masuk durable memory.

### 6. 🛡️ Approval, Safety, dan Idempotensi

- Email/message eksternal, calendar mutation, posting sosial, transaksi, destructive external-data change, dan account modification memerlukan approval eksplisit yang scoped ke action tersebut.
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
                              Role-aware Skill Router
                                      │
                 ┌────────────────────┼────────────────────┐
                 ▼                    ▼                    ▼
            Manager Agent       Marketing Agent       Advisor Agent
                 └────────────────────┼────────────────────┘
                                      ▼
        ┌────────────────────────────────────────────────────────┐
        │ Shared subsystems                                      │
        │ • Task engine + bounded handoff/retry                  │
        │ • Hybrid long-term memory: SQLite + FTS5 + sqlite-vec │
        │ • Markdown memory mirror                              │
        │ • Modular SKILL.md catalog                            │
        │ • Approval gateway + idempotent tool policy           │
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

## 🚀 Quickstart

### 1. Requirements

- Python 3.11+
- Git

### 2. Clone & install

```powershell
git clone https://github.com/Luciansvon/Morrow-AI.git
cd Morrow-AI
pip install -r requirements.txt
```

### 3. Environment

```powershell
cp .env.example .env
```

Minimum setup:

```env
OPENROUTER_API_KEY=your_openrouter_api_key_here

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

Konfigurasi embedding memory, dimension, timeout, model routing, dan limit lainnya tersedia di `.env.example` / `src/core/config.py`.

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

### 6. Run

```powershell
python -m src.main
```

Startup normal menginisialisasi database serta long-term memory indexes/mirror sebelum adapter Telegram mulai menerima pesan.

---

## 💬 Contoh

| Pesan | Owner / Capability |
|---|---|
| `Manager, prioritaskan backlog ini` | Manager + `prioritization_triage` |
| `Marketing, riset kompetitor lalu bikin positioning` | Marketing + `market_research` + `audience_positioning` |
| `Advisor, buat pre-mortem rencana ini` | Advisor + `risk_premortem` |
| `cek asumsi di dokumen ini` + PDF | Role owner + `document_inspection` + `assumption_audit` bila trigger cocok |
| `semua, bantu strategi launch` | bounded multi-agent collaboration dengan coordinator |
| `/approve appv_12345` | approval gateway untuk action eksternal yang sudah diproposalkan |

---

## 📂 Struktur Repositori

```text
Morrow-AI/
├── skills/                    # Katalog 16 modular SKILL.md
│   ├── manager/
│   ├── marketing/
│   ├── advisor/
│   └── shared/
├── docs/                      # Architecture, decisions, testing, worklog, backlog
├── src/
│   ├── adapters/              # Telegram multi-bot + CLI
│   ├── agents/                # Independent role runtimes
│   ├── approval/              # Scoped external-action approval
│   ├── core/                  # Orchestrator, config, shared types
│   ├── files/                 # Native parsers, OCR, vision pipeline
│   ├── llm/                   # Provider client, policy, usage metering
│   ├── memory/                # Hybrid retrieval, vector index, Markdown vault, judge
│   ├── routing/               # Addressing, intent, role routing, task analysis
│   ├── safety/                # Conflict detector + loop guard
│   ├── skills/                # SKILL.md loader, registry, router
│   ├── storage/               # SQLite schema/driver + attachments
│   ├── tasks/                 # Task lifecycle + handoff
│   └── tools/                 # Tool registry/execution policy
├── tests/                     # Unit, integration, regression, hardening
├── Morrow_PRD_v0.2_Skill_Based.md
├── pyproject.toml
└── requirements.txt
```

---

## 📜 License

Morrow AI dilisensikan di bawah [MIT License](LICENSE).
