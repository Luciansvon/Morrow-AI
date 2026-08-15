# 🤖 Morrow AI — Personal Autonomous Multi-Agent Executive Team

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Architecture](https://img.shields.io/badge/Architecture-1%20Backend%20%7C%203%20Telegram%20Bots-success.svg)](docs/ARCHITECTURE.md)
[![Tests](https://img.shields.io/badge/Tests-48%20Passed%20(100%25)-brightgreen.svg)](tests/)
[![PRD Compliance](https://img.shields.io/badge/PRD%20v0.2-22%20Contracts%20Verified-blueviolet.svg)](Morrow_PRD_v0.2_Skill_Based.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Morrow AI** adalah platform tim eksekutif multi-agen otonom pribadi yang beroperasi secara harmonis di dalam grup Telegram pengguna. Dibangun di atas **satu backend runtime terpadu**, Morrow menghadirkan **tiga agen spesialis independen** (Manager, Marketing, dan Advisor) dengan identitas bot masing-masing, sistem memori terisolasi, orkestrasi tugas idempoten, dan penanganan dokumen lokal pra-routing.

---

## 🌟 Fitur Utama (Key Capabilities)

### 1. 🎭 3 Bot Telegram Terpisah pada 1 Backend Terpadu
* **Manager Bot** (`@your_manager_bot`): Koordinasi tim, penentuan prioritas tugas, pelacakan dependensi, dan delegasi spesialis.
* **Marketing Bot** (`@your_marketing_bot`): Strategi kampanye, riset pasar, wawasan pelanggan, konten kreatif, dan copywriting persuasif.
* **Advisor Bot** (`@your_advisor_bot`): Analisis risiko bisnis, evaluasi untung-rugi (*trade-offs*), pertimbangan hukum/finansial, dan mitigasi krisis.
* **Satu Runtime Bersama:** Berbagi satu database SQLite (WAL mode), satu task system, satu shared memory, dan satu orchestrator tanpa dependensi aplikasi ganda.

### 2. 🗣️ Collective & Multi-Agent Addressing Cerdas
* **Social Broadcast (Mode A):** Sapaan ramah seperti *"halo semua"*, *"pagi tim"*, atau *"kalian gimana?"* dibalas oleh seluruh agen secara ringkas tanpa membuat tugas baru atau mencemari memori jangka panjang.
* **Multi-Agent Collaboration (Mode B):** Permintaan kerja tim seperti *"semua, bantu strategi launch"* dipandu oleh Manager sebagai *Discussion Coordinator* dengan batasan putaran aman (`LoopGuard`).
* **Object Quantifier Protection (Mode C):** Perintah dengan kata "semua" pada objek (*"hitung semua harga ini"*, *"cek semua produk"*, *"hapus semua task selesai"*) secara semantik **tidak memicu broadcast**, melainkan diteruskan ke tepat satu agen spesialis.

### 3. 💰 Model Routing Super Hemat & Akurat
* **Router & Memory Judge:** `MiMo-V2.5 non-thinking` untuk ekstraksi JSON kilat & zero-token waste.
* **Manager & Advisor Harian:** `DeepSeek V4 Flash 0731` dengan efisiensi tinggi dan penalaran terstruktur.
* **Marketing Spesialis:** `MiniMax M3` untuk evaluasi visual, materi promosi, dan spreadsheet kompleks.
* **Eskalasi Kritis:** `DeepSeek V4-Pro-0813` untuk keputusan bisnis berisiko tinggi (*irreversible*).
* **Failover Otomatis:** `GPT-5.6 Luna` saat provider utama mengalami gangguan / rate-limit.

### 4. 📁 Ekstraksi Berkas Pra-Routing (Native Parsing)
* Parsing berkas dilakukan **sebelum tahap routing** sehingga Router memahami konteks lengkap dokumen.
* Mendukung ekstraksi lokal untuk **Spreadsheet** (`.xlsx`, `.csv`), **Dokumen** (`.docx`), **Presentasi** (`.pptx`), **PDF**, dan **OCR/Visual Multimodal** (`.png`, `.jpg`).

### 5. 🛡️ Keamanan Eksekusi & Idempotensi Tindakan Luar
* Setiap tindakan berisiko (kirim email, modifikasi database, pembayaran) mewajibkan persetujuan manusia via token *Approval Gateway* sekali pakai (one-shot).
* Mutasi parameter setelah persetujuan otomatis membatalkan token (*SHA-256 Fingerprint Protection*).
* Deteksi konflik instruksi dan pembatasan maksimal 4 putaran diskusi tim (`LoopGuard`) mencegah *infinite loops*.

---

## 🏛️ Arsitektur Sistem

```text
                                Grup Telegram (Morrow.CO)
                 ┌────────────────────┬────────────────────┐
                 │    Manager Bot     │   Marketing Bot    │    Advisor Bot
                 └─────────┬──────────┴─────────┬──────────┴─────────┬──────┘
                           │                    │                    │
                           └────────────────────┼────────────────────┘
                                                ▼
                                    ONE MORROW BACKEND RUNTIME
                                                │
                                    ┌───────────────────────┐
                                    │ Telegram Normalizer   │ (Deduplication & Anti-Echo Filter)
                                    └───────────┬───────────┘
                                                ▼
                                    ┌───────────────────────┐
                                    │ Addressing & Intent   │ (Social / Work / Object Quantifier)
                                    └───────────┬───────────┘
                                                ▼
                                    ┌───────────────────────┐
                                    │  System Orchestrator  │ (Per-Group Concurrency Lock)
                                    └───────────┬───────────┘
                                                │
        ┌───────────────────────────────────────┼───────────────────────────────────────┐
        ▼                                       ▼                                       ▼
 ┌───────────────┐                       ┌───────────────┐                       ┌───────────────┐
 │ Manager Agent │                       │Marketing Agent│                       │ Advisor Agent │
 └───────┬───────┘                       └───────┬───────┘                       └───────┬───────┘
         │                                       │                                       │
         └───────────────────────────────────────┼───────────────────────────────────────┘
                                                 ▼
        ┌───────────────────────────────────────────────────────────────────────────────┐
        │ SUBSISTEM BERSAMA (SHARED SUBSYSTEMS)                                         │
        │ • SQLite DB (14 Tables, WAL Mode, message_agent_map, usage_ledger)            │
        │ • Task Engine & Anti-Cycle Handoff Guard                                      │
        │ • Multi-Layer Memory (Role vs Shared Memory) & Background Memory Judge        │
        │ • Modular Skill System (SKILL.md loader) & Idempotent Tool Policy             │
        │ • Approval Gateway (SHA-256 Fingerprinting) & Loop Guard (Max 4 Turns)        │
        └───────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Panduan Memulai Cepat (Quickstart)

### 1. Kebutuhan Sistem
* Python 3.12 atau versi lebih baru.
* Git.

### 2. Kloning Repositori & Pasang Dependensi
```powershell
git clone https://github.com/Luciansvon/Morrow-AI.git
cd Morrow-AI
pip install -r requirements.txt
```

### 3. Konfigurasi Lingkungan (`.env`)
Salin template berkas lingkungan dan isi token yang diperlukan:
```powershell
cp .env.example .env
```

Sesuaikan isi `.env`:
```env
OPENROUTER_API_KEY=your_openrouter_api_key_here

TELEGRAM_MANAGER_BOT_TOKEN=your_telegram_manager_bot_token_here
TELEGRAM_MARKETING_BOT_TOKEN=your_telegram_marketing_bot_token_here
TELEGRAM_ADVISOR_BOT_TOKEN=your_telegram_advisor_bot_token_here

TELEGRAM_ALLOWED_GROUP_IDS=-100xxxxxxxxxx
TELEGRAM_WHITELIST_USER_IDS=xxxxxxxxx

MORROW_ENV=development
LOG_LEVEL=INFO
DATABASE_PATH=./data/morrow.db
```

### 4. Konfigurasi BotFather (Wajib untuk 3 Bot)
Buka `@BotFather` di Telegram untuk masing-masing bot Anda:
* `/setjoingroups` → Pilih bot → **Enable** (Izinkan masuk grup).
* `/setprivacy` → Pilih bot → **Disable** (Izinkan membaca pesan grup).
* Masukkan ketiga bot ke grup Telegram tim Anda.

### 5. Menjalankan Pengujian Otomatis
```powershell
python -m pytest -v
```

### 6. Menjalankan Backend Morrow
```powershell
python -m src.main
```

Saat startup berhasil, console akan menampilkan:
```text
============================================================
  🚀 Memulai Asisten Tim AI Morrow v0.2
============================================================
✅ Database initialized
✅ Manager bot connected (@your_manager_bot)
✅ Marketing bot connected (@your_marketing_bot)
✅ Advisor bot connected (@your_advisor_bot)
✅ Allowed group loaded (1 group: -100xxxxxxxxxx)
✅ Whitelist loaded (1 user: xxxxxxxxx)
🚀 Morrow ready - Menunggu pesan di grup Telegram...
```

---

## 💬 Contoh Penggunaan di Grup Telegram

| Pesan Pengguna | Respon Sistem | Keterangan |
|---|---|---|
| `halo semua` | **Manager Bot**, **Marketing Bot**, **Advisor Bot** membalas sapaan singkat secara terpisah. | *Social Broadcast* (Mode A) |
| `Manager dan Marketing, halo` | **Manager Bot** dan **Marketing Bot** membalas sapaan. | *Multiple Agents Social* |
| `Manager, buat rencana launch produk A` | **Manager Bot** menyusun rencana kerja, lalu mendelegasikan kampanye ke **Marketing Bot** yang langsung menyambung pesan berikutnya. | *Backend-Controlled Delegation* |
| `hitung semua harga ini` | Tepat **satu bot spesialis** yang menjawab. | *Object Quantifier* (Bukan broadcast) |
| `/approve appv_12345` | Menyetujui tindakan luar berisiko (misal kirim email ke klien). | *Approval Gateway* |

---

## 📂 Struktur Repositori

```text
Morrow-AI/
├── .env.example               # Template variabel lingkungan aman
├── .gitignore                 # Proteksi token, db, dan berkas rahasia
├── pyproject.toml             # Konfigurasi dependensi, pytest & ruff
├── requirements.txt           # Daftar paket Python
├── Morrow_PRD_v0.2_Skill_Based.md # Spesifikasi PRD v0.2
├── docs/                      # Dokumentasi teknis lengkap
│   ├── ARCHITECTURE.md        # Arsitektur rinci & spesifikasi teknis
│   ├── DECISIONS.md           # Catatan Keputusan Arsitektur (ADR-001 s.d. ADR-012)
│   ├── TESTING_GUIDE.md       # Panduan eksekusi pengujian
│   └── WORKLOG.md             # Riwayat log kerja pengembangan
├── src/                       # Kode sumber utama
│   ├── adapters/              # Adapter Telegram multi-bot & CLI
│   │   ├── cli.py
│   │   └── telegram/          # bot_registry, update_normalizer, sender, adapter
│   ├── agents/                # Runtime & prompt spesialis (manager, marketing, advisor)
│   ├── approval/              # Approval gateway & fingerprinting
│   ├── core/                  # Orchestrator, normalizer, config, types
│   ├── files/                 # Parser spreadsheet, PDF, docx, pptx, OCR, vision
│   ├── llm/                   # OpenRouter client, model catalog, usage meter, policy
│   ├── memory/                # Role memory, shared memory, memory judge
│   ├── routing/               # Addressing detector, intent detector, fast-path, role router
│   ├── safety/                # Conflict detector & loop guard (max 4 turns)
│   ├── skills/                # Parser SKILL.md & skill registry
│   ├── storage/               # Schema SQL (14 tables), SQLite WAL driver, attachments
│   └── tools/                 # Tool registry, execution policy & idempotency
└── tests/                     # 48 Suite Pengujian Otomatis (100% Pass)
```

---

## 📜 Lisensi

Proyek ini dilisensikan di bawah [MIT License](LICENSE).
Dikembangkan untuk koordinasi tim AI multi-agen otonom tingkat lanjut.
