# 🏛️ Catatan Keputusan Arsitektur & Desain (ADR) — Morrow v0.2
*Status: `[TERVERIFIKASI]` — Berdasarkan Keputusan Resmi [`Morrow_PRD_v0.2_Skill_Based.md`](file:///c:/Users/shint/Downloads/AI-TEAM-MAS%20FENDI/Morrow_PRD_v0.2_Skill_Based.md)*

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
3. **Penyedia LLM (OpenRouter & Model Bertingkat):** Menggunakan OpenRouter API sebagai satu pintu terpadu dengan strategi model bertingkat (*Tiered Model Routing*):
   - **`deepseek/deepseek-chat` (DeepSeek V3/V4):** Otak utama agen Manager, Marketing, dan penyalur pesan (*Router*). Sangat hemat ($0.14 input / $0.28 output per 1M token) dan mendukung *prompt caching* hingga diskon 80%.
   - **`google/gemini-2.0-flash`:** Untuk analisis lampiran gambar/poster (*Vision*) dan routing cepat ($0.10 input / $0.40 output).
   - **`deepseek/deepseek-r1`:** Untuk Advisor Agent khusus penalaran mendalam (*Deep Reasoning*) saat menganalisis risiko berat.
   - **`meta-llama/llama-3.3-70b-instruct:free`:** Jalur gratis untuk pengujian/development.

4. **Pembaca Berkas Asli (*Native Parsers*):** `PyMuPDF` (`fitz`) untuk PDF berbasis teks, `openpyxl` untuk XLSX, `python-docx` untuk DOCX, `python-pptx` untuk PPTX.
5. **OCR & Analisis Visual:** `Pillow` dan `pytesseract` / Vision API untuk dokumen pindaian dan poster promosi.
6. **Deteksi Berkas & Keamanan:** `puremagic` / `filetype` untuk deteksi tipe berkas melalui *magic bytes* guna mencegah *file spoofing*.
7. **Ketahanan Jaringan (*Resilience*):** `tenacity` untuk *retry* otomatis dengan *exponential backoff*.
8. **Adapter Chat:** `aiogram v3` (Telegram) dan `CLI/FastAPI` adapter dibungkus antarmuka `BaseChannelAdapter`.
9. **Kerangka Pengujian:** `pytest`, `pytest-asyncio`, dan `pytest-cov`.

#### 3. Dampak
Arsitektur kode tetap ramping, mudah diuji secara modular, tidak memiliki ketergantungan berlebih pada pihak ketiga, dan sepenuhnya memenuhi 22 Kontrak Penerimaan (*Acceptance Contracts*).

---

### [ADR-009] Arsitektur Model Hibrida Super-Efisien (Hasil Audit Komparasi 2026)

* **Tanggal:** 2026-08-15
* **Status Keputusan:** Accepted
* **Rujukan PRD:** `D-013`, `REQ-LLM-001..004`, `REQ-FIL-007..008`, `REQ-RTR-002..003`

#### 1. Konteks
Setelah dilakukan audit komparatif mendalam berbasis data benchmark riil, keandalan *tool calling*, dukungan multimodal, dan perubahan harga DeepSeek V4 (17 Agustus 2026), arsitektur model perlu disederhanakan agar biaya operasional minimal namun performa tetap maksimal.

#### 2. Keputusan Arsitektur Model
1. **Model Harian (2 Daily Drivers):**
   - `Manager`: **`DeepSeek V4 Flash 0731`** ($0.14/$0.28 per 1M) dengan *reasoning* bertingkat (*off/low/high/xhigh*).
   - `Marketing`: **`MiMo-V2.5`** ($0.14/$0.28 per 1M), native multimodal (teks, gambar, video, audio) dengan error *tool-call* hanya 0.49%.
   - `Advisor (Normal)`: **`DeepSeek V4 Flash 0731`** (*reasoning: high/xhigh*).
   - `Router` & `Memory Judge`: **`MiMo-V2.5 non-thinking`** untuk klasifikasi JSON instan.
2. **Model Spesialis & Eskalasi (2 Escalation Models):**
   - `Marketing (Pro Mode)`: **`MiniMax M3`** ($0.30/$1.20 per 1M) untuk kampanye penting, evaluasi spreadsheet kompleks, dan analisis kreatif multi-file.
   - `Advisor (Critical)`: **`DeepSeek V4-Pro-0813`** ($1.32/$3.96 per 1M) khusus untuk keputusan berdampak tinggi, multi-tradeoff, ketidakpastian tinggi, dan sulit dibatalkan (*irreversible*).
3. **Model Darurat & Validasi Independen (2 Emergency Models):**
   - `Provider Fallback`: **`GPT-5.6 Luna`** saat DeepSeek mengalami gangguan / rate limit.
   - `Critical Cross-Check`: **`Claude Sonnet 5`** untuk peninjauan kedua independen pada keputusan hukum/bisnis raksasa.
4. **Jalur Berkas:** Dokumen teks/tabel dibaca *native parser* lokal, pindaian/gambar dianalisis oleh `MiMo-V2.5`, dan kasus visual sulit dievaluasi oleh `MiniMax M3`.

#### 3. Dampak
Sistem hanya mengaktifkan 2 model harian super hemat untuk 95% beban kerja, memangkas biaya pemborosan token reasoning, dan menjaga stabilitas integrasi fungsi.

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



