# 🏛️ Catatan Keputusan Arsitektur & Desain (ADR) — Morrow v0.2
*Status: `[AKTIF - DIAUDIT v0.2.2]` — Keputusan diterapkan terhadap [`Morrow_PRD_v0.2_Skill_Based.md`](../Morrow_PRD_v0.2_Skill_Based.md); keputusan produk yang masih terbuka tetap dicatat sebagai OQ dan tidak dianggap selesai oleh test suite.*

Dokumen ini mencatat seluruh keputusan arsitektur utama (*Architectural Decision Records*) yang telah disepakati untuk proyek **Morrow**.

---

### [ADR-001] Model Multi-Agen Mandiri (Manager, Marketing, Advisor)

* **Tanggal:** 2026-08-15
* **Status Keputusan:** Accepted
* **Rujukan PRD:** `D-001`, `D-002`, `D-003`, `REQ-AGT-001..005`

#### 1. Konteks
Sistem membutuhkan tim kerja AI yang memiliki spesialisasi peran yang jelas di dalam grup percakapan pribadi.

#### 2. Opsi yang Dipertimbangkan
* **Opsi A (Satu Bot Berganti Topeng):** Menggunakan satu bot tunggal yang berganti kepribadian sesuai perintah. (Kekurangan: Konteks mudah tercampur dan tanggung jawab kabur).
* **Opsi B (3 Agen Mandiri):** Memisahkan sistem menjadi 3 agen independen: `manager`, `marketing`, dan `advisor` dengan memori dan tugas masing-masing.

#### 3. Keputusan
Memilih **Opsi B**. Setiap agen memiliki runtime dan memori mandiri. Identitas peran internal (`manager`, `marketing`, `advisor`) bersifat tetap, meskipun nama tampilannya dapat diubah oleh pengguna.

#### 4. Dampak
Masing-masing agen memiliki batasan peran yang tegas dan tidak boleh mengambil alih peran lain secara diam-diam.

---

### [ADR-002] Penyaluran Pesan: Pemilik Tunggal (*Single Primary Owner*) & Sadar Balasan (*Reply-Aware*)

* **Tanggal:** 2026-08-15
* **Status Keputusan:** Accepted
* **Rujukan PRD:** `D-004`, `REQ-RTR-001..006`, `INV-001`

#### 1. Konteks
Saat pengguna mengirim pesan di grup, sistem harus menentukan agen mana yang bertanggung jawab menanggapi tanpa menimbulkan kekacauan respon ganda.

#### 2. Keputusan
Setiap pesan masuk wajib dialokasikan ke **tepat satu agen penanggung jawab utama (*Single Primary Owner*)**. Jika pengguna membalas (*reply*) pesan spesifik dari salah satu agen, sistem secara otomatis mengarahkan respon balik ke agen tersebut (*reply-aware routing*).

#### 3. Dampak
Mencegah agen-agen menjawab secara serentak yang membingungkan pengguna di grup.

---

### [ADR-003] Pemisahan Memori Peran, Memori Bersama, dan Riwayat Audit

* **Tanggal:** 2026-08-15
* **Status Keputusan:** Accepted
* **Rujukan PRD:** `D-010`, `REQ-MEM-001..011`, `INV-006`, `INV-007`

#### 1. Konteks
Agen tidak boleh dibebani seluruh riwayat percakapan mentah dari agen lain karena akan memboroskan konteks dan menimbulkan kebingungan data.

#### 2. Keputusan
Sistem membagi memori menjadi tiga lapisan:
1. **Memori Peran (*Role Memory*):** Catatan internal milik masing-masing agen.
2. **Memori Bersama (*Shared Memory*):** Fakta, keputusan resmi, dan status proyek aktif yang disepakati bersama.
3. **Riwayat Audit (*Audit History*):** Catatan riwayat nilai masa lalu ketika ada keputusan baru yang menggantikan nilai lama.

#### 3. Dampak
Agen hanya membaca informasi yang relevan dengan tugasnya, namun data historis tetap terlacak dan aman.

---

### [ADR-004] Penyedia Penalaran Utama DeepSeek dengan Batasan Modular

* **Tanggal:** 2026-08-15
* **Status Keputusan:** Accepted
* **Rujukan PRD:** `D-013`, `REQ-LLM-001..002`, `TC-007`

#### 1. Konteks
Diperlukan model penalaran yang kuat dan hemat biaya untuk menggerakkan logika tim agen.

#### 2. Keputusan
DeepSeek ditetapkan sebagai penyedia LLM utama (*default provider*), namun implementasinya wajib dibungkus di balik antarmuka (*interface boundary*) yang modular agar mudah diganti dengan penyedia lain jika diperlukan di kemudian hari.

---

### [ADR-005] Batasan Otoritas: Tindakan Internal Otomatis vs Tindakan Eksternal Wajib Persetujuan Manusia

* **Tanggal:** 2026-08-15
* **Status Keputusan:** Accepted
* **Rujukan PRD:** `D-005`, `D-006`, `REQ-HND-001`, `REQ-EXT-001..010`, `INV-009`, `INV-010`

#### 1. Konteks
Agen harus dapat bekerja secara efisien tanpa terlalu sering meminta izin untuk hal kecil, namun tindakan berdampak nyata di luar sistem harus berada di bawah kendali manusia.

#### 2. Keputusan
* **Tindakan Internal (Otomatis):** Delegasi tugas antar agen, pencatatan memori, pembagian peran, dan analisis data internal dapat berjalan secara otomatis tanpa persetujuan manual pengguna.
* **Tindakan Eksternal (Wajib Persetujuan):** Pengiriman email, modifikasi kalender, unggah status media sosial, transaksi finansial, dan pengubahan akun eksternal wajib meminta persetujuan eksplisit pengguna (*explicit user approval*).

---

### [ADR-006] Penanganan Konflik Instruksi Manusia: Menjeda Otomatisasi

* **Tanggal:** 2026-08-15
* **Status Keputusan:** Accepted
* **Rujukan PRD:** `D-008`, `REQ-CNF-001..004`, `INV-011`

#### 1. Konteks
Jika terdapat dua instruksi yang saling bertentangan dari pengguna, sistem tidak boleh secara sepihak memenangkan instruksi yang terakhir masuk.

#### 2. Keputusan
Sistem wajib **menjeda (*pause*) otomatisasi tugas yang terdampak**, menjelaskan adanya pertentangan instruksi ke dalam grup, dan menunggu klarifikasi manusia sebelum melanjutkan.

---

### [ADR-007] Pembatasan Putaran Diskusi Antar Agen (*Anti-Loop*)

* **Tanggal:** 2026-08-15
* **Status Keputusan:** Accepted
* **Rujukan PRD:** `D-009`, `REQ-CHAT-001..007`, `INV-012`, `INV-013`

#### 1. Konteks
Percakapan otomatis antar agen dapat terjebak dalam perulangan tanpa akhir (*infinite loop*) jika tidak dibatasi.

#### 2. Keputusan
* Maksimal **4 putaran percakapan antar agen** per sesi diskusi otomatis.
* Melibatkan maksimal **3 agen**.
* Suatu tugas **dilarang diserahkan kembali** ke agen yang sudah pernah gagal mengerjakannya di rantai delegasi yang sama (*no cycling back*).
* Jika batas putaran habis dan tugas belum tuntas, status otomatis berubah menjadi `waiting_user`.

---

### [ADR-008] Pemilihan Tumpukan Teknologi & Alat Teruji untuk Implementasi MVP

* **Tanggal:** 2026-08-15
* **Status Keputusan:** Accepted
* **Rujukan PRD:** `TC-001..TC-011`, `REQ-FIL-001..011`, `REQ-LLM-001..004`, `REQ-ACC-001`

#### 1. Konteks
Sistem membutuhkan kombinasi pustaka (*libraries*) dan alat pemrograman yang terbukti stabil, didukung komunitas secara luas, aman, dan mematuhi batasan PRD (menghindari framework berat seperti LangGraph/CrewAI yang rentan *bloat* dan sulit diaudit).

#### 2. Pilihan Teknologi Terpilih
1. **Core & Asinkron:** `Python 3.11+ / 3.12+` dengan standar `asyncio` dan `Pydantic v2` untuk validasi data terstruktur.
2. **Database & Penyimpanan:** `aiosqlite` dengan mode `SQLite WAL (Write-Ahead Logging)` untuk penyimpanan tugas, memori peran, memori bersama, dan jejak audit.
3. **Penyedia LLM:** OpenRouter digunakan sebagai provider gateway modular. Pemilihan model spesifik pada ADR-008 **disupersesi oleh ADR-009** dan source of truth runtime berada di `src/llm/model_catalog.py` + `src/llm/model_policy.py`. Harga provider tidak dibekukan dalam ADR karena dapat berubah.

4. **Pembaca Berkas Asli (*Native Parsers*):** `PyMuPDF` (`fitz`) untuk PDF berbasis teks, `openpyxl` untuk XLSX, `python-docx` untuk DOCX, `python-pptx` untuk PPTX.
5. **OCR & Analisis Visual:** `Pillow` dan `pytesseract` / Vision API untuk dokumen pindaian dan poster promosi.
6. **Deteksi Berkas & Keamanan:** `puremagic` / `filetype` untuk deteksi tipe berkas melalui *magic bytes* guna mencegah *file spoofing*.
7. **Ketahanan Jaringan (*Resilience*):** `tenacity` untuk *retry* otomatis dengan *exponential backoff*.
8. **Adapter Chat:** `aiogram v3` (Telegram) dan `CLI/FastAPI` adapter dibungkus antarmuka `BaseChannelAdapter`.
9. **Kerangka Pengujian:** `pytest`, `pytest-asyncio`, dan `pytest-cov`.

#### 3. Dampak
Arsitektur kode tetap ramping dan dapat diuji secara modular. Kesesuaian PRD dinilai per Acceptance Contract; tidak ada klaim 22/22 sampai setiap AC memiliki bukti uji yang benar-benar sesuai definisinya.

---

### [ADR-009] Arsitektur Model Hibrida Super-Efisien (Hasil Audit Komparasi 2026)

> Harga/discount provider bersifat dinamis. Nama model di dokumen ini menjelaskan intent arsitektur; slug dan routing runtime yang berlaku tetap mengikuti `src/llm/model_catalog.py` dan `src/llm/model_policy.py`.

* **Tanggal:** 2026-08-15
* **Status Keputusan:** Accepted
* **Rujukan PRD:** `D-013`, `REQ-LLM-001..004`, `REQ-FIL-007..008`, `REQ-RTR-002..003`

#### 1. Konteks
Setelah dilakukan audit komparatif mendalam berbasis data benchmark riil, keandalan *tool calling*, dukungan multimodal, dan perubahan harga DeepSeek V4 (17 Agustus 2026), arsitektur model perlu disederhanakan agar biaya operasional minimal namun performa tetap maksimal.

#### 2. Keputusan Arsitektur Model
1. **Model Harian (2 Daily Drivers):**
   - `Manager`: **`DeepSeek V4 Flash 0731`** dengan *reasoning* bertingkat (*off/low/high/xhigh*).
   - `Marketing`: **`MiMo-V2.5`** sebagai model Marketing harian dan klasifikasi murah sesuai policy runtime.
   - `Advisor (Normal)`: **`DeepSeek V4 Flash 0731`** (*reasoning: high/xhigh*).
   - `Router` & `Memory Judge`: **`MiMo-V2.5 non-thinking`** untuk klasifikasi JSON instan.
2. **Model Spesialis & Eskalasi (2 Escalation Models):**
   - `Marketing (Pro Mode)`: **`MiniMax M3`** untuk kampanye penting, evaluasi spreadsheet kompleks, dan analisis kreatif multi-file.
   - `Advisor (Critical)`: **`DeepSeek V4-Pro-0813`** khusus untuk keputusan berdampak tinggi, multi-tradeoff, ketidakpastian tinggi, dan sulit dibatalkan (*irreversible*).
3. **Model Darurat & Validasi Independen (2 Emergency Models):**
   - `Provider Fallback`: **`GPT-5.6 Luna`** saat DeepSeek mengalami gangguan / rate limit.
   - `Critical Cross-Check`: **`Claude Sonnet 5`** untuk peninjauan kedua independen pada keputusan hukum/bisnis raksasa.
4. **Jalur Berkas:** Dokumen teks/tabel dibaca *native parser* lokal, pindaian/gambar dianalisis oleh `MiMo-V2.5`, dan kasus visual sulit dievaluasi oleh `MiniMax M3`.

#### 3. Dampak
Sistem memprioritaskan model harian yang hemat dan hanya menaikkan tier berdasarkan workload/risk. Harga provider dan proporsi penggunaan bukan bagian dari kontrak ADR; biaya aktual harus dibaca dari usage ledger.

---

### [ADR-010] Rekonstruksi Domain Layer, Pipeline Berkas Pra-Routing, dan Eksekusi Idempoten

* **Tanggal:** 2026-08-15
* **Status Keputusan:** Accepted
* **Rujukan PRD:** `INV-001..015`, `REQ-SKL-001..005`, `REQ-FIL-001..011`, `REQ-EXT-001..010`

#### 1. Konteks
Audit sistem mendeteksi potensi cacat semantik: (1) attachment diproses setelah routing, (2) arsitektur Skill modular (`ROLE -> SKILL -> TOOL`) hilang, (3) `orchestrator.py` berpotensi menjadi *god-object*, dan (4) aksi eksternal belum memiliki kontrak idempotensi.

#### 2. Keputusan Arsitektur
1. **Urutan Pipeline Pra-Routing:** Berkas lampiran wajib diekstraksi (struktural/OCR/Vision) terlebih dahulu sebelum diteruskan ke *Fast Path* dan *Role Router*, agar Router memiliki konteks penuh dari isi dokumen.
2. **Pemecahan Domain Layer:** Kode dipecah ke modul mandiri: `tasks/`, `memory/`, `skills/`, `tools/`, `llm/`, `approval/`, `files/`, `routing/`, `storage/`.
3. **Arsitektur Skill & Tool:** Memisahkan peran agen (`agents/`), keahlian terdaftar (`skills/`), dan eksekutor alat (`tools/`) sehingga peran tidak dikawinkan dengan fungsi hardcoded.
4. **Abstraksi Beban Kerja:** Model di-resolve via `ModelPolicy.resolve(role, workload, risk, modality)`.
5. **Idempotensi & Approval:** Tindakan luar wajib memiliki `approval_id`, `parameter_hash`, dan `idempotency_key`. Status `UNKNOWN` dilarang di-retry otomatis oleh `tenacity`.
6. **Durable Database:** Database SQLite dilengkapi 14 tabel termasuk `message_agent_map`, `processed_events`, dan `usage_ledger`.

#### 3. Dampak
Sistem mencapai tingkat kesiapan implementasi tinggi (Readiness 9/10+), bebas dari *god-object*, dan mematuhi seluruh batasan PRD v0.2.

---

### [ADR-011] Arsitektur 3 Bot Telegram Terpisah pada Satu Backend Morrow Terpadu

* **Tanggal:** 2026-08-15
* **Status Keputusan:** Accepted
* **Rujukan PRD:** `CAP-AGENTS`, `CAP-ROUTING`, `CAP-CHAT`, `INV-001`, `INV-002`, `AC-002..004`, `AC-021`

#### 1. Konteks
Kebutuhan interaksi pengguna grup menghendaki pengalaman percakapan tim AI nyata di mana masing-masing peran agen (Manager, Marketing, Advisor) memiliki identitas bot Telegram terpisah (`@ManagerBot`, `@MarketingBot`, `@AdvisorBot`), namun tetap dikendalikan oleh satu backend Morrow tunggal tanpa duplikasi database atau orchestrator terpisah.

#### 2. Keputusan Arsitektur
1. **Satu Backend Bersama:** Tetap menggunakan 1 backend Python, 1 SQLite WAL shared database, 1 orchestrator, 1 task system, 1 shared memory, dan 1 approval gateway.
2. **3 Token Bot Terpisah:** Menggunakan `TELEGRAM_MANAGER_BOT_TOKEN`, `TELEGRAM_MARKETING_BOT_TOKEN`, `TELEGRAM_ADVISOR_BOT_TOKEN` yang dibungkus `SecretStr` tanpa kebocoran log.
3. **Penyaringan Pesan Sendiri (*Self-Bot Echo Filter*):** `update_normalizer.py` memfilter ID bot sendiri untuk mencegah infinite loop ketika bot saling mendelegasikan tugas.
4. **Deduplikasi Update Serentak:** Update yang diterima ketiga bot dari pesan pengguna yang sama di-deduplikasi via `(platform, group_id, platform_message_id)`.
5. **Pengiriman Berbasis Peran (*Role-Based Dispatcher*):** Respon agen dikirim menggunakan bot yang mewakili `RoleID` pemilik tugas (misal respon Marketing selalu dikirim via Marketing Bot).
6. **Pemetaan Balasan (*Reply Mapping*):** Tabel `message_agent_map` mencatat `(platform_message_id, originating_role_id, bot_identity, group_id)`.

#### 3. Dampak
Sistem multi-bot Telegram beroperasi mulus, elegan, dan seluruh 32 skenario pengujian unit/integrasi lulus 100%.

---

### [ADR-012] Sistem Collective & Multi-Agent Addressing dan Intent Detection

* **Tanggal:** 2026-08-15
* **Status Keputusan:** Accepted
* **Rujukan PRD:** `INV-002`, `CAP-ROUTING`, `CAP-CHAT`, `AC-002..004`

#### 1. Konteks
Pengguna memerlukan kemampuan untuk menyapa atau menugaskan beberapa/seluruh agen secara alami (*"halo semua"*, *"pagi tim"*, *"Manager dan Marketing, halo"*), namun kata *"semua"* tidak boleh dianggap broadcast jika berkonteks sebagai penunjuk jumlah objek (*"hitung semua harga ini"*, *"cek semua produk"*).

#### 2. Keputusan Arsitektur
1. **Pemisahan Modul:** Dibangun modul `src/routing/addressing.py` dan `src/routing/intent.py` terpisah dari adapter Telegram.
2. **Addressing Types:** Mendukung `none`, `single_agent`, `multiple_agents`, dan `all_agents`.
3. **3 Mode Perilaku:**
   - **Mode A (Social Broadcast):** Sapaan sosial dibalas 1x pendek oleh seluruh bot yang disapa tanpa membuat task atau memori jangka panjang.
   - **Mode B (Multi-Agent Work Request):** Permintaan kerja kolaboratif dikoordinasikan oleh Manager sebagai *Discussion Coordinator* di bawah `LoopGuard`.
   - **Mode C (Object Quantifier / Normal Task):** Diteruskan ke 1 agen utama via `RoleRouter`.
4. **Penyesuaian Kontrak PRD `INV-002`:** Pengecualian multi-response resmi diakomodasi khusus untuk *Social Broadcast*.

#### 3. Dampak
Pengalaman percakapan terasa hidup dan alami tanpa perang saudara antar-bot atau kebocoran memori. Seluruh 48 skenario pengujian unit dan integrasi lulus 100%.





