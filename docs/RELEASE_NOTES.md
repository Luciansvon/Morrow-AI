# Release Notes - Morrow

## [v0.2.2] - 2026-08-15
**Status:** reliability-hardening candidate, wajib lolos CI sebelum merge ke `main`.

Rilis ini berasal dari audit source 5-pass. Fokusnya bukan menambah gimmick baru, melainkan menutup failure mode yang bisa membuat Morrow salah routing, salah mengklaim delivery, salah menandai task selesai, mengulang side effect, atau mengonsumsi resource file secara tak terbatas.

Perubahan utama:
- Telegram sender fail-fast, tanpa message ID palsu.
- Explicit multi-agent addressing mendukung registered bot username dan tidak kalah oleh object quantifier `semua`.
- Collective work hanya `done` bila kontribusi/sintesis yang diwajibkan benar-benar selesai.
- Approval transitions atomic; execution claim dan idempotency diperketat.
- Tool policy fail-closed untuk action yang belum diklasifikasikan.
- OOXML/image/spreadsheet processing diberi resource caps.
- Vision usage diatribusikan ke group/thread budget.
- Parsing/validasi file sinkron dipindah ke worker thread agar satu upload berat tidak membekukan event loop semua grup.
- Reply routing dapat memakai identitas bot Telegram langsung, sehingga reply ke chunk awal pesan panjang tetap kembali ke role yang benar.
- Single-connection SQLite diberi transaction boundary yang mencegah coroutine lain ikut meng-commit transaksi aktif; legacy duplicate memory juga dideduplikasi sebelum unique index dibuat.
- Context dan output LLM dibatasi eksplisit (message/memory/tasks/output token), routing budget memakai pre-call cost estimate, dan normal task membawa thread cost attribution.
- Attachment storage mengikuti runtime `STORAGE_DIR` secara lazy.
- Task history API ditambahkan untuk status terminal.
- Source version diselaraskan ke `0.2.2`.
- CI tidak lagi auto-fix source secara diam-diam dan menguji Python 3.11 serta 3.12.
- Klaim lama “22 acceptance contracts verified 100%” dicabut karena test sebelumnya memetakan beberapa AC ke perilaku yang berbeda dari PRD.

### Acceptance status
Automated tests tetap memverifikasi access control, routing, dedup, handoff/anti-cycle, memory isolation/audit, file intake/parser, loop guard, approval safety, concurrency, model request wiring, dan regression hardening. Kontrak yang bergantung pada OQ-002/OQ-003/OQ-004/OQ-005 atau connector eksternal nyata tetap dicatat sebagai pending, bukan dipalsukan hijau.

## [v0.2.1] - 2026-08-15
Reliability foundation untuk 3 Telegram bot dalam satu backend: atomic event dedup, group-scoped memory, attachment pre-routing, model policy/reasoning pass-through, approval infrastructure, durable tool idempotency, dan regression suite.

## [v0.2.0] - 2026-08-15
Implementasi awal arsitektur modular Morrow. Catatan historis rilis ini sebelumnya menyatakan seluruh 22 acceptance contract sudah terverifikasi; audit v0.2.2 menemukan klaim tersebut terlalu luas dan mengoreksinya.

## [v0.1.0] - 2026-08-14
Dokumen inisiasi awal konsep tim AI pribadi Morrow.
