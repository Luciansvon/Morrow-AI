# 🏗️ Arsitektur & Struktur Proyek — Morrow v0.2
*Status: `[AKTIF - DIAUDIT v0.2.4]` — Rujukan produk: [`Morrow_PRD_v0.2_Skill_Based.md`](../Morrow_PRD_v0.2_Skill_Based.md). Tidak semua Acceptance Contract diklaim terotomasi.*

Dokumen ini menjelaskan arsitektur teknis, susunan komponen, pembagian peran agen, dan batasan teknologi untuk proyek **Morrow** (Asisten Tim AI Pribadi dalam Grup Percakapan).

---

## 1. Ikhtisar Produk (*Product Overview*)

Morrow adalah sistem asisten grup multi-agen pribadi (*private multi-agent group assistant*) yang beroperasi layaknya sebuah tim kerja kecil di dalam grup percakapan. Sistem ini tidak menggabungkan semua kepribadian ke dalam satu bot percakapan tunggal, melainkan menjalankan 3 agen independen yang dapat berbagi tugas, mendelegasikan pekerjaan, dan berkoordinasi secara otomatis.

Pengalaman percakapan ditargetkan terasa seperti berbicara dengan rekan yang punya karakter dan memori, bukan UI chatbot yang terus menjelaskan dirinya sendiri. Naturalitas ini tidak boleh berubah menjadi penipuan identitas: bila ditanya langsung, agent tetap menyatakan bahwa ia agent AI Morrow dan tidak mengarang pengalaman fisik atau riwayat hidup.

---

## 2. Struktur Agen, Peran, dan Persona

Morrow v0.2 memiliki 3 agen mandiri dengan identitas peran (*Role ID*) permanen:

| ID Peran | Nama Agen | Tanggung Jawab Utama | Persona Kultural |
|---|---|---|---|
| `manager` | **Manager Agent** | Koordinasi tim, prioritas, task, jadwal, dependensi, delegasi. | Millennial Indonesia / early-internet native |
| `marketing` | **Marketing Agent** | Kampanye, positioning, riset pasar, audience, content, measurement. | Gen Z Indonesia / modern-internet native |
| `advisor` | **Advisor Agent** | Keputusan, risiko, trade-off, skenario, rekomendasi. | Older Indonesian / Boomer-inspired cultural lens |

Persona disimpan sebagai layer tersendiri di `src/persona/`. Persona mengatur cultural memory, pola humor, ritme komunikasi, cross-generation familiarity, dan mode casual vs serious. Persona **tidak** mengubah role authority, tool permission, safety policy, atau fakta yang tersedia.

---

## 3. Peta Kemampuan Sistem (*Capability Map*)

1. **`CAP-ACCESS` (Akses & Keamanan):** hanya pengguna dan grup allowlisted yang dapat mengakses tim.
2. **`CAP-AGENTS` (Agen Mandiri):** runtime mandiri untuk masing-masing role.
3. **`CAP-PERSONA` (Persona Kultural):** karakter, humor, cultural memory, dan conversational cadence terpisah dari role/skill.
4. **`CAP-ROUTING` (Penyalur Pesan):** memilih satu primary owner dan mendukung reply-aware routing.
5. **`CAP-SKILLS` (Keahlian/Skills):** capability modular per role/shared.
6. **`CAP-TOOLS` (Agent Tool Runtime):** OpenRouter server tools + local user-defined tools dengan bounded loop dan policy fail-closed.
7. **`CAP-TASKS` (Siklus Tugas):** status `todo`, `in_progress`, `blocked`, `waiting_user`, `done`, `failed`, `cancelled`.
8. **`CAP-HANDOFF` (Delegasi):** perpindahan ownership internal antar-agent.
9. **`CAP-MEMORY` (Manajemen Memori):** role/shared memory, hybrid retrieval, audit history.
10. **`CAP-FILES` (Pemrosesan Berkas):** native parser, OCR, vision untuk attachment.
11. **`CAP-CHAT` (Diskusi Antar Agen):** collective discussion yang dibatasi budget/loop guard.
12. **`CAP-ACTIVITY` (Progress Preview):** status kerja sementara di Telegram + typing action.
13. **`CAP-BROWSER` (Browser Contract):** interface backend-agnostic dengan klasifikasi READ/PREPARE/COMMIT.
14. **`CAP-APPROVAL` (Persetujuan Tindakan Luar):** approval eksplisit sebelum external mutation.
15. **`CAP-SAFETY` (Perlindungan):** conflict detector, loop budget, dedup, attachment trust boundary.

---

## 4. Batasan & Pilihan Teknologi (*Technical Constraints*)

* **Model AI:** provider/model dipilih melalui `ModelPolicy`; OpenRouter menjadi gateway dan memungkinkan server tools lintas-model.
* **Structured storage:** SQLite menjadi durable source of truth.
* **Memory retrieval:** FTS5 + semantic embedding/`sqlite-vec` bila tersedia, dengan fallback lexical.
* **File storage:** berkas asli tetap di filesystem/object storage, bukan di prompt/memory blob.
* **Concurrency:** lock per-grup; transaksi SQLite dibuat pendek dan tidak mencakup panggilan LLM/network.
* **Supported files:** `PDF`, `DOCX`, `XLSX`, `CSV`, `TXT`, `MD`, `PPTX`, `PNG`, `JPG/JPEG`, `WEBP`.
* **Browser backend:** tidak ada hard dependency ke Ego Lite/Playwright/provider tertentu. Contract hidup di `src/browser/`.
* **Side effects:** browser COMMIT, email, calendar, social post, transaction, dan mutasi akun wajib approval.

---

## 5. Tool Architecture

### 5.1 Server tools

Tool yang dioperasikan OpenRouter dikirim langsung melalui `tools` array:

```text
openrouter:web_search  -> current/public information
openrouter:web_fetch   -> fetch/extract URL content
openrouter:datetime    -> current date/time in MORROW_TIMEZONE
```

Server tools dieksekusi oleh OpenRouter, bukan `tool_executor` lokal.

### 5.2 User-defined local tools

Local tools didaftarkan ke `ToolRegistry` dengan:

- function coroutine;
- description;
- JSON Schema parameters;
- optional eligible roles.

Tool schema diberikan ke model sebagai standard function tool. Ketika model memanggilnya, `AgentRuntime` menjalankan bounded loop:

```text
LLM -> function call -> ToolPolicy -> ToolExecutor -> tool result -> LLM -> final response
```

Tool pertama yang aktif adalah `calculate`, sebuah evaluator aritmetika berbasis AST tanpa `eval()` atau arbitrary code execution.

### 5.3 Fail-closed policy

`ToolPolicy` wajib mengetahui tool sebelum tool dapat dieksekusi. Tool unknown gagal dengan `TOOL_POLICY_UNCLASSIFIED`. External actions tidak dapat dieksekusi tanpa approval/idempotency.

---

## 6. Browser Boundary

`BrowserBackend` memisahkan Morrow dari implementasi browser tertentu dan mengambil ide task-space/control handoff tanpa menjadikan provider tertentu sebagai dependency wajib.

Action class:

- **READ**: navigate, inspect, snapshot, screenshot;
- **PREPARE**: perubahan lokal/session seperti mengisi draft yang belum dikirim;
- **COMMIT**: submit/send/post/purchase/delete atau external mutation lain.

`COMMIT` harus dikonversi menjadi external action dan melewati approval gateway sebelum backend menjalankannya. Handoff ke user dipakai untuk login, captcha, atau review manual; agent tidak boleh merebut control kembali tanpa explicit continuation.

---

## 7. Susunan Berkas Proyek & Domain Layer

```text
Morrow-AI/
├── Morrow_PRD_v0.2_Skill_Based.md
├── PROMPT_TEMPLATES.md
├── user.md
├── docs/
│   ├── ARCHITECTURE.md
│   ├── BUG_BACKLOG.md
│   ├── DECISIONS.md
│   ├── ERROR_SOLUTIONS.md
│   ├── RELEASE_NOTES.md
│   ├── TESTING_GUIDE.md
│   └── WORKLOG.md
└── src/
    ├── adapters/        # Telegram/CLI + activity lifecycle
    ├── agents/          # role runtimes + bounded tool loop
    ├── approval/        # approval gateway + fingerprints
    ├── browser/         # backend-neutral browser contract
    ├── core/            # orchestrator/config/types
    ├── files/           # native parsers/OCR/vision
    ├── llm/             # OpenRouter/provider/model policy/usage
    ├── memory/          # hybrid retrieval/vector index/vault/judge
    ├── persona/         # generational/cultural personas
    ├── routing/         # addressing/intent/role/social/task analysis
    ├── safety/          # conflict/loop guards
    ├── skills/          # SKILL.md loader/registry/router
    ├── storage/         # SQLite + attachment metadata
    ├── tasks/           # lifecycle/handoff
    └── tools/           # registry/builtins/server tools/policy/executor
```

---

## 8. Pipeline Runtime

```text
Event
  -> Adapter
  -> Normalize + Access
  -> Dedup
  -> Attachment Intake
  -> Addressing + Intent
  -> Social Fast Path OR Primary Role
  -> Persona Layer
  -> Skill Router
  -> Relevant Memory + Active Tasks
  -> Telegram Activity Preview
  -> Agent Execution
       -> OpenRouter server tools (0..N, provider-managed)
       -> Local function tools (bounded client loop)
  -> Response
  -> Activity Cleanup
  -> Task/Memory Judge
```

Simple greetings stay zero-token. Rich social banter runs through persona-aware `CASUAL` workload. Work remains role-routed and budgeted.

---

## 9. Model AI Hibrida (Audit 15 Agustus 2026)

> **Catatan operasional:** harga provider bersifat dinamis dan bukan kontrak arsitektur. ID model serta kebijakan routing yang berlaku ditentukan oleh `src/llm/model_catalog.py` dan `src/llm/model_policy.py`; biaya aktual dicatat melalui usage ledger.

1. **Daily drivers:** Manager/Advisor memakai DeepSeek sesuai policy; Marketing memakai model multimodal sesuai catalog/policy.
2. **Eskalasi:** workload/risk dapat menaikkan model ke tier yang lebih kuat.
3. **Fallback:** provider client memiliki fallback konservatif untuk transient failure.
4. **Files:** structured docs dibaca native; image/scanned docs menggunakan vision/OCR sesuai pipeline.
5. **Tools:** model yang dipilih tetap dapat menerima OpenRouter server tools dan standard function tools selama provider route mendukung parameter tools.
