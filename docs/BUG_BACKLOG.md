# Bug & Risk Backlog - Morrow v0.2.2

Status ini mencerminkan source code setelah audit reliability 5-pass pada 2026-08-15. Dokumen ini memisahkan **bug implementasi yang sudah ditutup** dari **keputusan produk yang memang masih terbuka**. Keduanya tidak boleh dicampur hanya demi badge hijau yang terlihat menenangkan.

## Bug implementasi yang ditutup

- **AUD5-001 Telegram delivery integrity:** sender tidak lagi membuat `message_id` sintetis ketika bot belum siap. Kegagalan delivery sekarang menjadi error nyata.
- **AUD5-002 Addressing precedence:** explicit role/bot username menang atas kata `semua` yang hanya mengkuantifikasi objek.
- **AUD5-003 Collective completion:** task kolaborasi tidak lagi otomatis `done` bila budget/loop menghentikan diskusi sebelum lengkap; status menjadi `waiting_user`. Exception saat eksekusi membuat task `blocked`.
- **AUD5-004 Approval race:** approve/reject/execution claim memakai transaksi dan conditional state transition.
- **AUD5-005 Idempotency binding:** satu idempotency key terikat ke tool + parameter yang sama; reuse berbeda ditolak.
- **AUD5-006 Tool policy:** aksi yang belum diklasifikasikan gagal tertutup (`TOOL_POLICY_UNCLASSIFIED`) dan tidak dianggap internal otomatis.
- **AUD5-007 Attachment persistence:** file unsupported/spoofed tidak dibiarkan tersimpan sebagai attachment valid.
- **AUD5-008 Archive/image resource limits:** OOXML dibatasi jumlah entry dan ukuran uncompressed; gambar dibatasi total piksel; spreadsheet dibaca bounded/read-only.
- **AUD5-009 Storage config:** attachment storage membaca `STORAGE_DIR` secara lazy sehingga tidak membekukan path saat import.
- **AUD5-010 Vision cost attribution:** pemakaian model vision membawa `group_id/thread_id` ke usage ledger.
- **AUD5-011 Duplicate multimodal spend:** agent utama memakai text modality setelah preprocessor vision menghasilkan deskripsi terstruktur, sehingga raw image tidak dibayar dua kali tanpa kebutuhan.
- **AUD5-012 Test integrity:** klaim palsu `22/22 acceptance contracts verified` dihapus. Test otomatis hanya mengklaim perilaku yang benar-benar diuji.
- **AUD5-013 Release/CI consistency:** versi diselaraskan ke v0.2.2; Ruff sekarang verification-only dan CI menguji Python 3.11 + 3.12.
- **AUD5-014 Event-loop isolation:** parser/validator Office, PDF, OCR, image, dan disk attachment yang sinkron dijalankan via `asyncio.to_thread` pada pipeline async.
- **AUD5-015 Reply chunk integrity:** reply ke pesan bot dapat dirutekan langsung dari Telegram bot user ID ke `RoleID`, tidak bergantung hanya pada mapping chunk terakhir di database.
- **AUD5-016 SQLite transaction isolation:** ordinary DB calls dan explicit transaction tidak lagi dapat berbagi commit boundary secara tidak sengaja pada satu koneksi async.
- **AUD5-017 Legacy memory migration:** duplicate active memory dari schema lama dilipat ke row terbaru sebelum unique index dibuat sehingga upgrade tidak gagal di startup.
- **AUD5-018 LLM bounds/cost controls:** message, memory, active-task context, dan output token dibatasi; routing memakai cost estimate terhadap `BUDGET_ROUTING_PER_MESSAGE`, normal request memakai `BUDGET_NORMAL_TASK`, dan usage memakai thread ID yang konsisten.

## Keputusan produk yang sudah dipakai oleh implementasi

### OQ-001 Routing precedence - ACCEPTED
Urutan deterministic fast path:
1. explicit named role / registered bot username,
2. reply context,
3. active task ownership/continuity,
4. semantic router.

Kata kolektif seperti `semua` hanya menjadi all-agent address bila konteksnya vocative/team address. Quantifier objek seperti `hitung semua harga` tidak memanggil semua agent.

### OQ-006 Approval lifecycle - ACCEPTED
- approval bersifat one-shot,
- exact parameter hash wajib sama,
- perubahan parameter membatalkan izin lama,
- execution memakai durable idempotency key,
- hasil eksternal `unknown` tidak di-retry otomatis,
- duplicate execution tidak boleh menggandakan side effect.

## Keputusan produk yang masih terbuka

### OQ-002 / OQ-004 Retry dan terminal failure - OPEN
`TaskService` memiliki retry counter dan status `failed`, tetapi orchestrator tidak mengarang kebijakan retry/handoff otomatis sampai budget retry per-agent vs per-task diputuskan.

### OQ-003 Repeat participation - OPEN
Loop guard membatasi maksimal 4 turns dan 3 agents. Aturan semantik kapan agent yang sama boleh bicara lagi karena membawa informasi baru masih perlu keputusan produk eksplisit.

### OQ-005 Multi-user conflict authority - OPEN
Instruksi manusia yang berkonflik dapat menjeda task ke `waiting_user`, tetapi aturan siapa yang berwenang menyelesaikan konflik antar dua user whitelist belum ditentukan.

## Batas implementasi saat ini

Connector eksternal nyata seperti email, calendar, payment, dan social posting belum otomatis tersedia hanya karena approval infrastructure ada. Tool harus terdaftar dan punya policy classification; jika tidak, sistem gagal secara aman.
