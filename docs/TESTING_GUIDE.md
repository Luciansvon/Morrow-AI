# 🧪 Panduan Pengujian (Testing Guide) — Morrow v0.2
*Status: `[CONTRACT-ORIENTED / DIAUDIT v0.2.2]` — Skenario diturunkan dari [`Morrow_PRD_v0.2_Skill_Based.md`](../Morrow_PRD_v0.2_Skill_Based.md). Daftar ini tidak berarti seluruh AC sudah memiliki automated evidence.*

Dokumen ini berisi prosedur dan skenario pengujian untuk memverifikasi persyaratan produk Morrow. Status tiap kontrak harus berasal dari bukti uji yang benar-benar menguji perilaku kontrak tersebut, bukan hanya dari nama atau nomor test.

---

## 1. Prinsip Utama Pengujian (*Evidence-First*)
* Dilarang mengklaim pengujian "berhasil" tanpa bukti eksekusi nyata (*terminal output* atau hasil status tes).
* Hasil audit/rilis penting dicatat di [`WORKLOG.md`](WORKLOG.md), sedangkan bukti otomatis utama berasal dari output CI/test run.
* Setiap skenario pengujian di bawah ini terhubung langsung dengan ID Kontrak Penerimaan (*Acceptance Contract ID*).
* Tidak boleh ada test agregat yang menandai AC sebagai `PASSED` tanpa mengeksekusi assertion yang relevan terhadap definisi AC tersebut.

---

## 2. Matriks Skenario Pengujian Sistem

### A. Pengujian Akses & Identitas Pengguna

| ID Tes | Rujukan | Skenario Uji Coba | Hasil yang Diharapkan (*Expected Result*) | Tanda Kegagalan |
|---|---|---|---|---|
| **`TC-ACC-01`** | `AC-001` | Pengguna yang tidak terdaftar di daftar putih (*whitelist*) mengirim pesan ke grup. | Pesan diabaikan dan tidak masuk ke proses penalaran agen mana pun. | Agen membalas atau memproses pesan pengguna tak dikenal. |
| **`TC-ACC-02`** | `AC-002` | Nama tampilan (*display name*) Manager diubah oleh pengguna. | Identitas internal tetap `manager` dan routing pesan tetap berjalan lancar. | Sistem gagal mengenali agen atau salah kirim peran. |

---

### B. Pengujian Penyaluran Pesan & Delegasi (*Routing & Handoff*)

| ID Tes | Rujukan | Skenario Uji Coba | Hasil yang Diharapkan (*Expected Result*) | Tanda Kegagalan |
|---|---|---|---|---|
| **`TC-RTR-01`** | `AC-003` | Pengguna mengirim pesan ambigu yang relevan untuk beberapa agen. | Sistem memilih **tepat satu agen utama** sebagai penanggung jawab awal. | Banyak agen menjawab bersamaan atau tidak ada yang menjawab. |
| **`TC-RTR-02`** | `AC-004` | Pengguna membalas (*reply*) pesan yang sebelumnya dikirim oleh Marketing Agent. | Pesan balasan langsung diteruskan kembali ke Marketing Agent. | Pesan dialihkan ke Manager atau terjadi kegagalan routing. |
| **`TC-HND-01`** | `AC-005` | Manager Agent mendelegasikan tugas internal yang berkaitan dengan riset ke Marketing Agent. | Tugas berpindah ke Marketing Agent secara otomatis tanpa meminta izin manual pengguna; konteks tugas tetap utuh. | Sistem berhenti meminta izin pengguna untuk aksi internal. |
| **`TC-HND-02`** | `AC-006` | Tugas yang gagal dicoba dialihkan dari Manager ➡️ Marketing ➡️ Manager lagi. | Penyerahan kedua ke Manager ditolak (*anti-looping*); sistem mencari opsi lain atau eskalasi ke manusia. | Tugas berputar-putar tanpa henti antara kedua agen. |

---

### C. Pengujian Pemrosesan Berkas (*File Intake*)

| ID Tes | Rujukan | Skenario Uji Coba | Hasil yang Diharapkan (*Expected Result*) | Tanda Kegagalan |
|---|---|---|---|---|
| **`TC-FIL-01`** | `AC-007` | Pengguna mengunggah berkas Excel (`.xlsx`) valid. | Berkas dibaca langsung strukturnya (*native parser*), bukan melalui OCR teks gambar. | Pembacaan gagal atau format tabel menjadi acak-acakan. |
| **`TC-FIL-02`** | `AC-008` | Pengguna mengunggah berkas PDF hasil pindai/foto (*scanned PDF tanpa text layer*). | Sistem otomatis menggunakan jalur OCR/Vision dan melaporkan hasil ekstraksi secara jujur. | Sistem mengarang isi berkas atau gagal membaca tanpa fallback. |
| **`TC-FIL-03`** | `AC-009` | Pengguna mengunggah gambar poster promosi yang membutuhkan analisis desain dan teks. | Informasi visual dan teks hasil ekstraksi keduanya tersedia untuk agen penanggung jawab. | Hanya teks yang terbaca atau konteks visual hilang. |
| **`TC-FIL-04`** | `AC-018` | Pengguna mengunggah dokumen referensi untuk dianalisis sementara. | Hasil ekstraksi digunakan untuk menjawab, namun **tidak otomatis disimpan permanen** ke memori jangka panjang. | Memori bersama tercemar oleh isi seluruh berkas mentah. |

---

### D. Pengujian Manajemen Memori & Jejak Audit

| ID Tes | Rujukan | Skenario Uji Coba | Hasil yang Diharapkan (*Expected Result*) | Tanda Kegagalan |
|---|---|---|---|---|
| **`TC-MEM-01`** | `AC-010` | Keputusan jadwal peluncuran diubah dari tanggal A menjadi tanggal B. | Memori aktif menampilkan tanggal B, dan riwayat audit mencatat jejak perubahan dari A ke B beserta pelakunya. | Nilai lama hilang tanpa jejak atau memori aktif masih memakai nilai A. |
| **`TC-MEM-02`** | `AC-019` | Marketing menanggapi tugas setelah oper alih (*handoff*) dari Manager. | Marketing hanya menerima ringkasan tugas dan memori bersama yang relevan, tanpa dibebani seluruh riwayat obrolan mentah Manager. | Konteks memori bocor berlebihan (*context pollution*). |

---

### E. Pengujian Penanganan Konflik & Keamanan

| ID Tes | Rujukan | Skenario Uji Coba | Hasil yang Diharapkan (*Expected Result*) | Tanda Kegagalan |
|---|---|---|---|---|
| **`TC-CNF-01`** | `AC-011` / `AC-015` | Muncul instruksi baru yang bertentangan dengan instruksi sebelumnya dari pengguna. | Sistem menjeda otomatisasi tugas, menjelaskan pertentangan di grup, dan menunggu klarifikasi manusia. | Sistem langsung menimpa data tanpa konfirmasi (*latest message wins*). |
| **`TC-SEC-01`** | `AC-016` | Agen mengusulkan tindakan mengirim email ke pihak luar. | Sistem meminta persetujuan eksplisit pengguna dan **tidak mengirim sebelum disetujui**. | Email terkirim otomatis tanpa izin pengguna. |
| **`TC-SEC-02`** | `AC-017` | Pengguna menolak (*reject*) usulan pengiriman pesan eksternal. | Tindakan langsung dibatalkan dan tidak ada efek samping ke luar. | Tindakan tetap berjalan sebagian atau terjadi error fatal. |
| **`TC-SEC-03`** | `AC-021` | Pesan atau notifikasi yang sama terkirim dua kali dari aplikasi chat (*duplicate event*). | Sistem menyaring duplikasi sehingga tidak membuat tugas atau aksi ganda. | Tugas tercatat dua kali di database. |
