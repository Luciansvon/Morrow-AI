# 🏗️ Arsitektur & Struktur Proyek — Morrow v0.2
*Status: `[TERVERIFIKASI]` — Berdasarkan [`Morrow_PRD_v0.2_Skill_Based.md`](file:///c:/Users/shint/Downloads/AI-TEAM-MAS%20FENDI/Morrow_PRD_v0.2_Skill_Based.md)*

Dokumen ini menjelaskan arsitektur teknis, susunan komponen, pembagian peran agen, dan batasan teknologi untuk proyek **Morrow** (Asisten Tim AI Pribadi dalam Grup Percakapan).

---

## 1. Ikhtisar Produk (*Product Overview*)

Morrow adalah sistem asisten grup multi-agen pribadi (*private multi-agent group assistant*) yang beroperasi layaknya sebuah tim kerja kecil di dalam grup percakapan. Sistem ini tidak menggabungkan semua kepribadian ke dalam satu bot percakapan tunggal, melainkan menjalankan 3 agen independen yang dapat berbagi tugas, mendelegasikan pekerjaan, dan berkoordinasi secara otomatis.

---

## 2. Struktur Agen & Pembagian Peran

Morrow v0.2 memiliki 3 agen mandiri dengan identitas peran (*Role ID*) permanen:

| ID Peran (*Role ID*) | Nama Agen | Tanggung Jawab Utama |
|---|---|---|
| `manager` | **Manager Agent** | Koordinasi tim, penentuan prioritas, manajemen tugas, penjadwalan, pelacakan dependensi, dan delegasi pekerjaan. |
| `marketing` | **Marketing Agent** | Strategi kampanye, *positioning* merek, riset pasar, wawasan pelanggan, strategi konten, dan analisis performa pemasaran. |
| `advisor` | **Advisor Agent** | Analisis keputusan, evaluasi risiko, pertimbangan *trade-off*, rekomendasi strategis, serta analisis dampak jangka pendek & panjang. |

---

## 3. Peta Kemampuan Sistem (*Capability Map*)

1. **`CAP-ACCESS` (Akses & Keamanan):** Memastikan hanya pengguna dan grup percakapan yang terdaftar dalam daftar putih (*whitelist/allowlist*) yang dapat mengakses tim AI.
2. **`CAP-AGENTS` (Agen Mandiri):** Runtime mandiri untuk masing-masing peran agen.
3. **`CAP-ROUTING` (Penyalur Pesan):** Memilih satu agen utama (*single primary owner*) untuk setiap pesan masuk dan mendukung pelacakan balasan pesan (*reply-aware routing*).
4. **`CAP-SKILLS` (Keahlian/Skills):** Kemampuan modular yang dapat digunakan oleh peran tertentu atau dibagikan ke beberapa peran.
5. **`CAP-TASKS` (Siklus Tugas):** Penyimpanan dan pelacakan status tugas (`todo`, `in_progress`, `blocked`, `done`, `cancelled`).
6. **`CAP-HANDOFF` (Delegasi & Oper Alih):** Perpindahan kepemilikan tugas antar agen tanpa perlu meminta izin persetujuan manual pengguna untuk tugas internal.
7. **`CAP-MEMORY` (Manajemen Memori):** Pemisahan antara memori peran (*role memory*), memori bersama (*shared memory*), dan riwayat audit perubahan (*audit history*).
8. **`CAP-FILES` (Pemrosesan Berkas):** Analisis dokumen asli (*native parser* untuk XLSX, PDF, DOCX, CSV, dll.) serta pembaca teks/gambar (*OCR & Vision*) untuk dokumen hasil pindai.
9. **`CAP-CHAT` (Diskusi Antar Agen):** Ruang percakapan otomatis antar agen yang dibatasi maksimal 4 putaran dan 3 agen untuk mencegah perulangan tanpa henti.
10. **`CAP-APPROVAL` (Persetujuan Tindakan Luar):** Wajib meminta izin persetujuan eksplisit dari pengguna sebelum menjalankan aksi ke dunia luar (kirim email, ubah kalender, transaksi, posting media sosial).
11. **`CAP-SAFETY` (Perlindungan & Batasan):** Pendeteksi konflik instruksi manusia, batas perulangan (*loop budget*), dan pencegahan duplikasi pesan.

---

## 4. Batasan & Pilihan Teknologi (*Technical Constraints*)

Berdasarkan bagian `TC-001` s.d. `TC-011` pada PRD:

* **Model Kecerdasan Buatan (LLM):** DeepSeek sebagai penyedia penalaran utama secara *default*, namun terpasang di balik antarmuka modular sehingga dapat diganti di masa depan (*interchangeable provider*).
* **Penyimpanan Data Terstruktur:** Menggunakan **SQLite** untuk menyimpan data tugas, konfigurasi, dan memori terstruktur.
* **Penyimpanan Berkas Asli:** Berkas fisik disimpan terpisah di sistem penyimpanan berkas (*filesystem/object storage*), bukan dicampur di dalam memori AI.
* **Penyimpanan Vektor:** Tidak menggunakan basis data vektor (*vector DB*) untuk kebutuhan MVP agar sistem tetap sederhana dan andal.
* **Pengendalian Konkurensi:** Penguncian dan penanganan pesan dilakukan per-grup/per-utas percakapan, tanpa kunci global (*no global lock*) yang dapat memblokir grup lain.
* **Format Berkas yang Didukung:** `PDF`, `DOCX`, `XLSX`, `CSV`, `TXT`, `MD`, `PPTX`, `PNG`, `JPG/JPEG`, `WEBP`.

---

## 5. Susunan Berkas Proyek & Domain Layer

```text
📁 AI-TEAM-MAS FENDI/
├── 📄 Morrow_PRD_v0.2_Skill_Based.md   (Sumber spesifikasi utama produk)
├── 📄 PROMPT_TEMPLATES.md              (Kumpulan cetakan prompt dokumentasi)
├── 📄 user.md                          (Profil preferensi interaksi pengguna)
├── 📁 docs/                            (Pusat dokumentasi proyek)
│   ├── 📄 ARCHITECTURE.md              (Dokumen arsitektur ini)
│   ├── 📄 BUG_BACKLOG.md               (Catatan risiko & kendala yang belum selesai)
│   ├── 📄 DECISIONS.md                 (Catatan keputusan arsitektur / ADR)
│   ├── 📄 ERROR_SOLUTIONS.md           (Riwayat kendala nyata & solusinya)
│   ├── 📄 RELEASE_NOTES.md             (Catatan rilis versi produk)
│   ├── 📄 TESTING_GUIDE.md             (Panduan pengujian & skenario uji coba)
│   ├── 📄 WORKLOG.md                   (Buku riwayat pekerjaan harian)
│   └── 📁 archive/                     (Folder penyimpanan dokumen usang)
│       └── 📄 README.md                (Indeks berkas arsip)
└── 📁 src/                             (Kode sumber sistem berbasis Domain Layer)
    ├── 📁 core/                        (Orkestrasi event loop & normalizer)
    ├── 📁 routing/                     (Fast-path & semantic role router)
    ├── 📁 agents/                      (Runtime independen: Manager, Marketing, Advisor)
    ├── 📁 skills/                      (Loader SKILL.md, registry & skill router)
    ├── 📁 tools/                       (Tool registry, policy & idempotent executor)
    ├── 📁 tasks/                       (Task lifecycle, dependency, retry, handoff)
    ├── 📁 memory/                      (Memory service, judge, shared facts, audit)
    ├── 📁 llm/                         (Provider, OpenRouter, ModelPolicy, usage meter)
    ├── 📁 files/                       (Intake, native parsers, extraction, OCR, vision)
    ├── 📁 safety/                      (Conflict detector, anti-loop guard)
    ├── 📁 approval/                    (Approval gateway, fingerprinting)
    ├── 📁 storage/                     (SQLite WAL, 14 tabel relasional, sandboxed files)
    └── 📁 adapters/                    (Telegram aiogram v3 & CLI adapter)
```

---

## 6. Arsitektur Pipeline & Model AI Hibrida (Audit 15 Agustus 2026)

### A. Urutan Alur Peristiwa (Event Pipeline)
```text
Event ➡️ Adapter ➡️ Normalize/Access Check ➡️ Dedup ➡️ Attachment Intake (Native/OCR/Vision)
➡️ Fast-Path Router ➡️ Role Router ➡️ Primary Agent ➡️ Skill Router ➡️ Agent Execution
➡️ Task/Memory/Handoff ➡️ Memory Judge ➡️ Response Channel
```

### B. Alokasi Model Berbasis Beban Kerja (`ModelPolicy.resolve`)
1. **Model Harian (Daily Drivers - 2 Model):**
   - **`manager` (Planning):** `DeepSeek V4 Flash 0731` ($0.14/$0.28 per 1M token) dengan penalaran dinamis (*low/high/xhigh*).
   - **`marketing` (Konten/Visual):** `MiMo-V2.5` ($0.14/$0.28 per 1M token), native multimodal teks dan gambar.
   - **`advisor` (Normal):** `DeepSeek V4 Flash 0731` (*reasoning: high*).
   - **`router` & `memory_judge`:** `MiMo-V2.5 (non-thinking)` untuk klasifikasi JSON instan.
2. **Model Spesialis & Eskalasi (2 Model):**
   - **`marketing` (Creative Pro):** `MiniMax M3` ($0.30/$1.20 per 1M token) untuk kampanye besar dan spreadsheet rumit.
   - **`advisor` (Critical Decision):** `DeepSeek V4-Pro-0813` ($1.32/$3.96 per 1M token) khusus keputusan berisiko tinggi dan sulit dibatalkan (*irreversible*).
3. **Cadangan & Peninjau Independen (2 Model):**
   - **Cadangan Darurat (*Provider Fallback*):** `GPT-5.6 Luna` saat DeepSeek mengalami *outage* atau rate limit.
   - **Peninjau Kedua (*Cross-Check*):** `Claude Sonnet 5` untuk keputusan hukum/bisnis raksasa.
4. **Jalur Berkas (MVP: Tanpa Audio/Video):**
   - XLSX, DOCX, PPTX, PDF teks dibaca langsung oleh parser Python lokal (*native parser*).
   - Pindaian dokumen / poster visual dianalisis oleh `MiMo-V2.5` (dengan eskalasi ke `MiniMax M3` untuk kasus visual yang sangat rumit).


