# 📋 Kumpulan Prompt Template — Folder `docs/`
*Proyek: Morrow — Asisten Tim AI Pribadi*

Dokumen ini berisi **prompt siap pakai** yang bisa kamu gunakan untuk mengisi dan memperbarui setiap berkas dokumentasi di folder `docs/`.

---

## 📂 Struktur Folder Dokumentasi

Berikut adalah susunan berkas dokumentasi yang ada di dalam proyek ini:

```text
📁 AI-TEAM-MAS FENDI/ (Folder Utama Proyek)
│
├── 📄 Morrow_PRD_v0.2_Skill_Based.md   (Spesifikasi utama sistem Morrow)
├── 📄 PROMPT_TEMPLATES.md              (Buku panduan cetakan prompt ini)
├── 📄 user.md                          (Catatan preferensi & profil pengguna)
│
└── 📁 docs/                            (Pusat dokumentasi proyek)
    ├── 📄 ARCHITECTURE.md              (Susunan arsitektur, peran agen & teknologi)
    ├── 📄 BUG_BACKLOG.md               (Daftar risiko teknis & keputusan terbuka)
    ├── 📄 DECISIONS.md                 (Catatan keputusan arsitektur / ADR)
    ├── 📄 ERROR_SOLUTIONS.md           (Riwayat kendala nyata & langkah solusinya)
    ├── 📄 RELEASE_NOTES.md             (Catatan riwayat versi produk)
    ├── 📄 TESTING_GUIDE.md             (Panduan & skenario pengujian fitur)
    ├── 📄 WORKLOG.md                   (Buku riwayat aktivitas kerja harian)
    │
    └── 📁 archive/                     (Folder penyimpanan dokumen usang)
        └── 📄 README.md                (Daftar berkas yang diarsipkan)
```

---

## 1. 🐛 ERROR_SOLUTIONS.md — Catat Error yang Sudah Terjadi

> **Kapan dipakai:** Setiap kali ada error/bug nyata yang **sudah terbukti terjadi** dan sudah diperbaiki (atau sedang dipantau).

### Prompt Template:

```
Catat error baru di docs/ERROR_SOLUTIONS.md dengan format berikut:

### [ERR-XXX] {Judul singkat error}

* **Status:** {Open / Resolved / Monitoring}
* **Tanggal Ditemukan:** {YYYY-MM-DD}
* **Area / File Terdampak:** `{path/to/file}`

#### 1. Gejala (Symptoms)
{Apa yang terjadi? Pesan error apa yang muncul di layar/konsol?}

#### 2. Cara Reproduksi (Steps to Reproduce)
1. {Langkah 1}
2. {Langkah 2}
3. {Langkah 3}

#### 3. Akar Masalah (Root Cause)
{Kenapa error ini bisa terjadi? Jelaskan berdasarkan investigasi.}

#### 4. Solusi & Perbaikan (Resolution)
{Apa yang sudah dilakukan untuk memperbaikinya?}

#### 5. Perlindungan Regresi (Regression Protection)
{Langkah pencegahan supaya error ini tidak terulang.}

#### 6. Bukti Verifikasi (Verification Proof)
{Output terminal / screenshot yang membuktikan error sudah selesai.}
```

### Contoh Prompt Penggunaan:
```
Catat error baru: Website gagal load gambar produk keychain-round.png karena path salah.
Status: Resolved. File terdampak: index.html dan assets/. Sudah diperbaiki 
dengan mengganti path relatif.
```

---

## 2. 📝 WORKLOG.md — Catat Riwayat Pekerjaan

> **Kapan dipakai:** Setiap kali ada pekerjaan yang selesai dilakukan — mau itu coding, desain, dokumentasi, atau perbaikan bug.

### Prompt Template:

```
Catat pekerjaan baru di docs/WORKLOG.md dengan format berikut:

### [WL-XXX] {Judul pekerjaan}
* **Tanggal:** {YYYY-MM-DD}
* **Tipe Pekerjaan:** {Coding / Desain / Dokumentasi / Perbaikan Bug / dll}
* **Status:** {In Progress / Completed}
* **Tujuan:** {Apa yang mau dicapai dari pekerjaan ini?}
* **Scope Pekerjaan:**
  - {Lingkup kerja 1}
  - {Lingkup kerja 2}
* **File yang Dibuat / Berubah:**
  - `[NEW]` / `[MODIFIED]` / `[DELETED]` [`{nama-file}`](file:///{path-lengkap})
* **Keputusan Penting:**
  - {Keputusan apa yang diambil selama proses kerja?}
* **Command / Uji Coba yang Dijalankan:**
  1. `{perintah terminal}`
     - *Hasil Aktual:* {output-nya apa?}
* **Hal yang Belum Diuji:**
  - {Apa yang belum sempat dicek?} `[BELUM DIUJI]`
* **Next Action:**
  - {Langkah selanjutnya yang perlu dikerjakan.}
```

### Contoh Prompt Penggunaan:
```
Catat worklog: Hari ini aku menambahkan animasi scroll reveal pada section 
"Our Story". File yang berubah: app.js dan styles.css. Belum diuji di mobile.
```

---

## 3. 🪲 BUG_BACKLOG.md — Catat Bug & Risiko yang Belum Selesai

> **Kapan dipakai:** Saat ada bug yang belum diperbaiki, atau risiko teknis yang mungkin jadi masalah di masa depan.

### Prompt Template — Bug Terverifikasi:

```
Catat bug baru di docs/BUG_BACKLOG.md bagian "Daftar Bug Terverifikasi":

### [BUG-XXX] {Judul bug}
* **Severity:** {Critical / High / Medium / Low}
* **Status:** {Open / In Progress / Resolved}
* **Tanggal Ditemukan:** {YYYY-MM-DD}
* **Bukti:** `[TERVERIFIKASI]` {Jelaskan bukti nyata — output terminal, screenshot, dll.}
* **Dampak:** {Apa efeknya ke pengguna/website?}
* **Root Cause:** {Kenapa bug ini terjadi?}
* **Next Action:** {Apa yang harus dilakukan untuk menyelesaikan ini?}
```

### Prompt Template — Risiko/Dugaan Masa Depan:

```
Catat risiko baru di docs/BUG_BACKLOG.md bagian "Catatan Risiko":

### [RSK-XXX] {Judul risiko}
* **Severity:** {Critical / High / Medium / Low} ({Jenis risiko: Performance / Security / Compatibility / dll})
* **Status:** {Open / Anticipated / Monitoring}
* **Bukti:** `[TERVERIFIKASI]` {Bukti kenapa ini dianggap berisiko.}
* **Dampak:** {Apa efeknya kalau risiko ini terjadi?}
* **Dugaan Root Cause:** {Kenapa risiko ini bisa muncul?}
* **Next Action:** {Rencana mitigasi atau langkah pencegahan.}
```

### Contoh Prompt Penggunaan:
```
Catat risiko baru: Font Google Fonts "Instrument Serif" bisa gagal load kalau 
pengguna offline. Severity Medium. Perlu sediakan fallback font lokal.
```

---

## 4. 🏛️ DECISIONS.md — Catat Keputusan Arsitektur (ADR)

> **Kapan dipakai:** Setiap kali ada keputusan teknis penting yang diambil — misalnya pilih teknologi, ubah struktur, atau ganti pendekatan desain.

### Prompt Template:

```
Catat keputusan arsitektur baru di docs/DECISIONS.md:

### [ADR-XXX] {Judul keputusan}

* **Tanggal:** {YYYY-MM-DD}
* **Status Keputusan:** {Proposed / Accepted / Superseded / Deprecated}

#### 1. Konteks
{Latar belakang: kenapa keputusan ini perlu diambil? Masalah apa yang dihadapi?}

#### 2. Opsi yang Dipertimbangkan
* **Opsi A:** {Deskripsi, kelebihan, kekurangan.}
* **Opsi B:** {Deskripsi, kelebihan, kekurangan.}

#### 3. Keputusan
{Opsi mana yang dipilih dan kenapa?}

#### 4. Dampak
{Konsekuensi positif dan negatif dari keputusan ini.}
```

### Contoh Prompt Penggunaan:
```
Catat keputusan: Kita memilih pakai Vanilla CSS tanpa framework (Tailwind/Bootstrap) 
karena sesuai prinsip anti-AI slop dan kontrol desain penuh. 
Alternatifnya adalah pakai Tailwind tapi terlalu generik.
```

---

## 5. 🚀 RELEASE_NOTES.md — Catat Rilis Versi

> **Kapan dipakai:** Saat website sudah siap dirilis atau ada milestone besar yang pantas dicatat.

### Prompt Template:

```
Catat rilis baru di docs/RELEASE_NOTES.md:

## [vX.Y.Z] - {YYYY-MM-DD}

### 1. Alasan Rilis
{Kenapa versi ini dirilis? Apa tujuan utamanya?}

### 2. Perubahan & Fitur Baru
* **Fitur:** {Fitur baru apa yang ditambahkan?}
* **Peningkatan:** {Optimasi apa yang dilakukan?}

### 3. Perbaikan Bug (Bug Fixes)
* {Bug apa yang diperbaiki? Rujuk ke ERR-XXX jika ada.}

### 4. Verifikasi Test & Build
* {Perintah yang dijalankan dan hasilnya.}

### 5. Target / Lingkungan Terdampak
* {Browser/perangkat/OS yang didukung.}

### 6. Isu yang Diketahui (Known Issues) & Kekurangan
* {Apa yang belum sempurna di versi ini?}

### 7. Artefak & Checksum (Jika Ada)
* {File build / hash SHA256.}
```

### Contoh Prompt Penggunaan:
```
Catat rilis v1.0.0: Landing page Pixel and Crafted versi pertama sudah selesai. 
Fitur: Hero section, katalog produk, navigasi scroll, halaman about. 
Belum ada: filter kategori dan integrasi Etsy.
```

---

## 6. 🧪 TESTING_GUIDE.md — Tambah Prosedur Pengujian Baru

> **Kapan dipakai:** Kalau ada fitur baru yang butuh cara uji coba spesifik.

### Prompt Template:

```
Tambahkan prosedur pengujian baru di docs/TESTING_GUIDE.md:

### {Nama Pengujian}
* **Tujuan:** {Apa yang mau dibuktikan dari pengujian ini?}
* **Prasyarat:** {Apa yang harus disiapkan sebelum menguji?}
* **Langkah Pengujian:**
  1. {Langkah 1}
  2. {Langkah 2}
  3. {Langkah 3}
* **Hasil yang Diharapkan:** {Apa yang seharusnya terjadi kalau berhasil?}
* **Hasil yang TIDAK Boleh Terjadi:** {Apa tanda kegagalan?}
```

### Contoh Prompt Penggunaan:
```
Tambah pengujian untuk animasi scroll reveal: 
Pastikan elemen-elemen di section Work muncul bertahap saat discroll ke bawah. 
Di mobile harus tetap smooth tanpa lag.
```

---

## 7. 🏗️ ARCHITECTURE.md — Perbarui Struktur Arsitektur

> **Kapan dipakai:** Kalau ada perubahan besar di struktur folder, file baru, teknologi baru, atau pola kode baru.

### Prompt Template:

```
Perbarui docs/ARCHITECTURE.md dengan informasi berikut:

* **Perubahan Struktur:**
  - {File/folder baru apa yang ditambahkan?}
  - {File/folder apa yang dihapus atau dipindahkan?}
* **Teknologi Baru (Jika Ada):**
  - {Library/tool baru apa yang dipakai? Kenapa?}
* **Pola/Komponen Baru:**
  - {Komponen atau pola kode baru apa yang diperkenalkan?}
```

### Contoh Prompt Penggunaan:
```
Update arsitektur: Ditambahkan folder components/ untuk modularisasi 
JavaScript. File app.js dipecah jadi navigation.js, catalog.js, dan animations.js.
```

---

## 8. 📦 docs/archive/README.md — Pindahkan File Usang

> **Kapan dipakai:** Kalau ada dokumen/file yang sudah tidak relevan tapi tidak boleh dihapus.

### Prompt Template:

```
Pindahkan file usang ke docs/archive/ dan catat di README.md:

### {Nama File yang Diarsipkan}
* **Tanggal Diarsipkan:** {YYYY-MM-DD}
* **Alasan:** {Kenapa file ini tidak lagi dipakai?}
* **Lokasi Asli:** `{path asli sebelum dipindah}`
* **Pengganti (Jika Ada):** {File baru yang menggantikan, atau "Tidak ada".}
```

### Contoh Prompt Penggunaan:
```
Arsipkan file desain lama: DESIGN-v1.md sudah digantikan oleh DESIGN.md 
yang lebih lengkap. Pindahkan ke archive.
```

---

## ⚡ Tips Pemakaian

| Situasi | File yang Diisi | Template # |
|---|---|---|
| Ada error/bug di website | `ERROR_SOLUTIONS.md` | #1 |
| Selesai ngerjain sesuatu | `WORKLOG.md` | #2 |
| Ada bug belum selesai / risiko | `BUG_BACKLOG.md` | #3 |
| Ambil keputusan teknis penting | `DECISIONS.md` | #4 |
| Website siap rilis | `RELEASE_NOTES.md` | #5 |
| Perlu cara uji fitur baru | `TESTING_GUIDE.md` | #6 |
| Struktur folder/tech berubah | `ARCHITECTURE.md` | #7 |
| File lama mau diarsipkan | `archive/README.md` | #8 |

> [!TIP]
> **Cara paling gampang:** Copas template di atas, ganti bagian yang di dalam `{kurung kurawal}` dengan info yang sebenarnya, lalu tempel ke file yang sesuai. Atau kalau mau aku yang bantu isi, tinggal bilang aja — kasih info mentahnya dan aku akan formatkan sesuai template.

> [!IMPORTANT]
> **Aturan Penting dari AGENTS.md:**
> - Jangan bikin data error/bug fiktif (palsu). Hanya catat yang **beneran terjadi**.
> - Setiap klaim "berhasil" harus ada **bukti output terminal/screenshot**.
> - Pakai label `[TERVERIFIKASI]`, `[PROPOSAL]`, `[PERLU KONFIRMASI]`, atau `[BELUM DIUJI]` di setiap catatan.
