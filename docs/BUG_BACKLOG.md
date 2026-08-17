# Bug & Risk Backlog - Morrow v0.2.6

Status ini mencerminkan audit ulang dispatch/reliability pada 2026-08-17. Bug implementasi dipisahkan dari keputusan produk yang memang masih terbuka; build hijau tetap bukan pengganti kontrak perilaku yang benar.

## Bug implementasi yang ditutup

- **AUD5-001 Telegram delivery integrity:** sender tidak membuat `message_id` sintetis ketika bot belum siap.
- **AUD5-002 Addressing precedence:** explicit role/bot username menang atas object quantifier `semua`.
- **AUD5-003 Collective completion:** budget/loop stop tidak boleh menghasilkan `done` palsu.
- **AUD5-004 Approval race:** approve/reject/execution claim memakai transaksi dan conditional state transition.
- **AUD5-005 Idempotency binding:** satu idempotency key terikat ke tool + parameter yang sama.
- **AUD5-006 Tool policy:** action yang belum diklasifikasikan gagal tertutup.
- **AUD5-007..018:** attachment/resource bounds, storage config, vision attribution, duplicate multimodal spend, test integrity, CI consistency, event-loop isolation, reply mapping, SQLite isolation, memory migration, dan LLM bounds tetap berlaku dari audit sebelumnya.

### AUD6-001 Natural collective addressing - CLOSED
`terimakasih semua`, `terima kasih semua`, `makasih semua`, dan bentuk `semua tolong/bantu/...` sekarang dipahami sebagai collective address tanpa bergantung pada koma. Object quantifier seperti `cek semua produk` tetap bukan broadcast.

### AUD6-002 Role-as-object ambiguity dan mention order - CLOSED
Bare `manager/marketing/advisor` hanya dianggap direct address pada leading vocative/imperative clause. Pertanyaan seperti `apa bedanya manager dan advisor` tidak memicu fan-out. Urutan textual role dipertahankan; Manager tetap coordinator bila memang termasuk target work.

### AUD6-003 Control intent / urgent stop - CLOSED
`stop`, `batal`, `jangan lanjut`, pause, dan resume ditangani sebagai control intent. Stop/pause tidak menunggu long-running group lock dan stale response yang selesai setelah cancellation tidak dikirim.

### AUD6-004 Collective per-agent completion - CLOSED
Setiap target collaboration mempunyai durable row di `task_agent_runs`. Kegagalan satu target tidak mencegah target berikutnya mencoba bekerja, tetapi task tetap `blocked` dan tidak dianggap `done` sampai seluruh target wajib sukses serta synthesis selesai.

### AUD6-005 Durable inbound event lifecycle - CLOSED
`processed_events` tidak lagi berarti “pernah disentuh”. Event memakai state `processing/completed/failed`, attempt counter, lease, dan reclaim setelah failure/abandoned lease. Duplicate bot menunggu hasil owner pertama dan hanya mengambil alih bila retry aman.

### AUD6-006 Task/thread continuity binding - CLOSED
Task baru dibind kembali ke `conversation_message_map` dan canonical inherited thread dipakai lintas runtime, budget, loop guard, dan handoff.

### AUD6-007 Router fallback observability - CLOSED
Semantic router tidak lagi menelan exception diam-diam. Budget fallback, low confidence, JSON/parse failure, dan runtime failure memiliki telemetry serta reason yang berbeda.

### AUD6-008 Browser COMMIT boundary - CLOSED
Browser backend menolak COMMIT tanpa approval proof meskipun dipanggil langsung. ToolExecutor menyuntikkan proof internal hanya pada eksekusi approval yang sah; state fingerprint tetap diverifikasi sebelum COMMIT.

### AUD6-009 Acceptance false positives - CLOSED
Live/post-merge acceptance tidak boleh memberi PASS hanya karena response non-empty. Multi-agent completion dibuktikan lewat `task_agent_runs`; evidence checks yang tidak memiliki provenance cukup menjadi `PARTIAL/FAIL`, bukan PASS dekoratif.

## Keputusan produk yang sudah dipakai oleh implementasi

### OQ-001 Routing precedence - ACCEPTED
Urutan deterministic fast path:
1. explicit direct role / registered bot username,
2. reply context,
3. active task ownership/continuity,
4. semantic single-owner router.

Collective addressing tetap dipisahkan dari single-primary-owner routing: social broadcast dapat membalas per-role, sedangkan work collective memakai coordinator + target ledger.

### OQ-006 Approval lifecycle - ACCEPTED
- approval one-shot,
- exact parameter/state binding,
- perubahan parameter/state membatalkan izin lama,
- execution memakai durable idempotency key,
- hasil eksternal `unknown` tidak di-retry otomatis,
- duplicate execution tidak menggandakan side effect.

## Keputusan produk yang masih terbuka

### OQ-002 / OQ-004 Retry dan terminal failure - OPEN
Per-agent failure sekarang tercatat dan target lain tetap dicoba. Kebijakan **retry otomatis** masih sengaja belum dibuat sampai budget retry per-agent vs per-task disepakati.

### OQ-003 Repeat participation - OPEN
Loop guard tetap membatasi maksimal 4 turns dan 3 agents. Kapan agent yang sama boleh bicara lagi karena informasi baru masih membutuhkan keputusan produk eksplisit.

### OQ-005 Multi-user conflict authority - OPEN
Instruksi manusia yang berkonflik dapat menjeda task, tetapi aturan otoritas antar beberapa user whitelist belum diputuskan.

## Batas implementasi saat ini

Connector eksternal nyata seperti email, calendar, payment, dan social posting tidak otomatis tersedia hanya karena approval infrastructure ada. Tool harus terdaftar dan punya policy classification; jika tidak, sistem gagal secara aman.
