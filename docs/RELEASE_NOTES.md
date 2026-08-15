# 🚀 Catatan Rilis Versi (Release Notes) — Morrow

Dokumen ini mencatat seluruh riwayat versi, status perubahan, dan kesiapan rilis untuk sistem **Morrow**.

---

## [v0.2.0] - 2026-08-15
* **Status:** `[RELEASED]` — *Implementasi Penuh & 22 Acceptance Contracts Terverifikasi 100%*
* **Rujukan Dokumen:** [`Morrow_PRD_v0.2_Skill_Based.md`](file:///c:/Users/shint/Downloads/AI-TEAM-MAS%20FENDI/Morrow_PRD_v0.2_Skill_Based.md)

### 1. Ringkasan Rilis
Morrow v0.2 telah selesai dibangun secara penuh menggunakan arsitektur modular Domain Layer (`src/core`, `src/agents`, `src/routing`, `src/skills`, `src/tools`, `src/tasks`, `src/memory`, `src/llm`, `src/files`, `src/safety`, `src/approval`, `src/storage`, `src/adapters`). Seluruh 22 Kontrak Penerimaan (AC-001 s.d. AC-022) berhasil lolos uji 100% pada suite pengujian otomatis (`pytest`).

### 2. Kapabilitas & Invarian Terverifikasi
* **Multi-Agent Runtime (`INV-001`, `AC-019`):** 3 agen mandiri (`manager`, `marketing`, `advisor`) dengan perakitan konteks terisolasi tanpa kebocoran riwayat mentah.
* **Deterministic Fast Path & Semantic Router (`INV-002`, `INV-003`, `AC-002`, `AC-003`, `AC-004`):** Penyaluran pesan ke TEPAT SATU agen utama dan pelacakan balasan pesan durable via tabel `message_agent_map`.
* **Ekstraksi Berkas Pra-Routing (`INV-007`, `AC-007`, `AC-008`, `AC-009`, `AC-018`):** Pembacaan berkas (XLSX, CSV, PDF, DOCX, PPTX, gambar) dilakukan sebelum pesan masuk ke router.
* **Skill Modular & Eksekusi Idempoten (`INV-004`, `AC-005`, `AC-016`, `AC-017`):** Dukungan pemuatan `SKILL.md`, isolasi kelayakan peran, dan eksekutor tool idempoten.
* **Delegasi Tugas & Anti-Cycle Guard (`INV-005`, `INV-013`, `AC-006`):** Siklus tugas internal dan pelarangan pengalihan tugas berulang ke agen yang pernah mencoba di rantai yang sama.
* **Memori Multi-Lapis & Audit History (`INV-006`, `AC-010`, `AC-012`):** Pemisahan memori peran vs memori bersama, serta pencatatan jejak riwayat perubahan keputusan lampau.
* **Gerbang Izin Aksi Luar & Anti-Mutasi (`INV-009`, `AC-013`, `AC-022`):** Wajib persetujuan eksplisit pengguna sebelum aksi luar dijalankan, dengan pembatalan otomatis jika parameter diubah.
* **Safety, Anti-Loop, & Concurrency Lock (`INV-008`, `INV-010`, `INV-014`, `INV-015`, `AC-001`, `AC-011`, `AC-014`, `AC-015`, `AC-020`, `AC-021`):** Pembatas 4 putaran diskusi otomatis, deteksi konflik instruksi manusia, kunci konkurensi per-grup (tanpa global lock), dan deduplikasi event masuk.


---

## [v0.1.0] - 2026-08-14
* **Status:** `[DEPRECATED]` (Telah diperbarui menjadi v0.2)
* **Keterangan:** Dokumen inisiasi awal konsep tim AI pribadi Morrow.
