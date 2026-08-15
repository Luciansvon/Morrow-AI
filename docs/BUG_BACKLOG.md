# 🪲 Daftar Masalah & Catatan Risiko (Bug & Risk Backlog) — Morrow v0.2
*Status: `[TERVERIFIKASI]` — Berdasarkan Bagian 14 PRD [`Morrow_PRD_v0.2_Skill_Based.md`](file:///c:/Users/shint/Downloads/AI-TEAM-MAS%20FENDI/Morrow_PRD_v0.2_Skill_Based.md)*

Dokumen ini mencatat masalah teknis (*bugs*) nyata serta catatan risiko keputusan terbuka (*open questions*) yang perlu diputuskan sebelum tahap implementasi otonom penuh dijalankan.

---

## 1. Daftar Masalah Terverifikasi (Bugs)

*Saat ini belum ada bug kode nyata karena repositori masih dalam tahap persiapan spesifikasi dan perencanaan dokumen.*

---

## 2. Catatan Potensi Risiko & Keputusan Tertunda (*Blocking Open Questions*)

Berikut adalah 6 poin keputusan arsitektur yang masih berstatus **`[PROPOSAL]` / `[PERLU KONFIRMASI]`** sebelum sistem dapat diimplementasikan secara otomatis:

### [RSK-001] Prioritas Penyaluran Pesan saat Terjadi Konflik Sinyal (OQ-001)
* **Severity:** High (Routing Architecture)
* **Status:** Open / `[PERLU KONFIRMASI]`
* **Tanggal Ditemukan:** 2026-08-15
* **Bukti:** PRD Bagian 14.3 (`OQ-001`)
* **Dampak:** Jika pengguna me-reply pesan Agen A tetapi teksnya menyebut nama Agen B, sistem belum memiliki urutan prioritas pasti sinyal mana yang dimenangkan.
* **Daftar Sinyal:** (1) Sebutan eksplisit nama agen, (2) Konteks balasan pesan, (3) Pemilik tugas saat ini, (4) Konteks percakapan, (5) Isi lampiran berkas, (6) Niat umum pengguna.
* **Next Action:** Menetapkan tabel prioritas urutan sinyal routing.

---

### [RSK-002] Alur Pemulihan Tugas yang Terblokir & Batas Percobaan Ulang (OQ-002 & OQ-004)
* **Severity:** High (Task Lifecycle)
* **Status:** Open / `[PERLU KONFIRMASI]`
* **Tanggal Ditemukan:** 2026-08-15
* **Bukti:** PRD Bagian 14.3 (`OQ-002`, `OQ-004`)
* **Dampak:** Perlu kepastian apakah batas 3 kali percobaan ulang (*retry*) berlaku global per tugas atau per agen, serta kepastian apakah status `failed` disimpan secara permanen di database.
* **Next Action:** Menyepakati alur: `Retry (3x) -> Delegasi ke Agen Lain -> Status Tertunda / Eskalasi ke Manusia`.

---

### [RSK-003] Aturan Partisipasi Ulang Agen dalam Percakapan Otomatis (OQ-003)
* **Severity:** Medium (Thread Semantics)
* **Status:** Open / `[PERLU KONFIRMASI]`
* **Tanggal Ditemukan:** 2026-08-15
* **Bukti:** PRD Bagian 14.3 (`OQ-003`)
* **Dampak:** Menghindari agen mengirim pesan duplikat atau pesan sekadar "setuju" yang menghabiskan kuota giliran diskusi.
* **Next Action:** Memilih aturan baku: Agen hanya boleh berbicara kembali jika membawa informasi baru atau tindakan nyata.

---

### [RSK-004] Otoritas Penyelesaian Konflik Dua Pengguna Berizin Sama (OQ-005)
* **Severity:** High (Multi-User Authority)
* **Status:** Open / `[PERLU KONFIRMASI]`
* **Tanggal Ditemukan:** 2026-08-15
* **Bukti:** PRD Bagian 14.3 (`OQ-005`)
* **Dampak:** Jika dua pengguna dalam grup memberikan instruksi yang bertolak belakang, sistem menjeda tugas tetapi membutuhkan aturan siapa atau format pesan apa yang sah untuk melanjutkan.
* **Next Action:** Menentukan format konfirmasi resolusi dari pengguna yang diakui sistem.

---

### [RSK-005] Siklus Hidup Izin Tindakan Eksternal (OQ-006)
* **Severity:** High (External Action Security)
* **Status:** Open / `[PERLU KONFIRMASI]`
* **Tanggal Ditemukan:** 2026-08-15
* **Bukti:** PRD Bagian 14.3 (`OQ-006`)
* **Dampak:** Menghindari tindakan ganda (*double execution*) atau eksekusi aksi luar yang parameternya sudah berubah setelah pengguna memberikan izin.
* **Next Action:** Menetapkan aturan bahwa izin bersifat 1 kali pakai (*one-shot*) dan perubahan parameter wajib meminta izin ulang.

---

### [RSK-006] Batasan Ukuran Berkas & Keamanan Jalur Sistem (OQ-009..011)
* **Severity:** Medium (Security & File Processing)
* **Status:** Open / `[PERLU KONFIRMASI]`
* **Tanggal Ditemukan:** 2026-08-15
* **Bukti:** PRD Bagian 14.4 (`OQ-009`, `OQ-010`, `OQ-011`)
* **Dampak:** Perlindungan dari unggahan berkas berukuran terlalu besar atau manipulasi nama berkas yang membahayakan sistem (*path traversal*).
* **Next Action:** Menentukan batas ukuran berkas maksimum (misal: 25MB) dan aturan validasi tipe berkas nyata (*magic bytes*).
