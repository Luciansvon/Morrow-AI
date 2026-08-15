---
name: assumption_audit
description: Mengaudit asumsi, uncertainty, confidence, kebutuhan validasi/verifikasi, dan fakta yang belum terbukti.
eligible_roles: [*]
triggers: [asumsi, assumption, ketidakpastian, uncertainty, confidence, yakin, validasi, verifikasi, fact check]
---
## Tujuan
Membuat asumsi yang memengaruhi keputusan terlihat dan memprioritaskan validasi yang paling bernilai.

## Workflow
1. Pisahkan fakta yang diberikan, inferensi, asumsi, dan unknown.
2. Untuk tiap asumsi material, nilai dampak bila salah dan seberapa mudah diverifikasi.
3. Prioritaskan asumsi high-impact/high-uncertainty; jangan memvalidasi trivia lebih dulu.
4. Jika verifikasi eksternal/tool tidak tersedia, jangan menyamarkannya sebagai sudah diverifikasi.
5. Perbarui rekomendasi hanya sejauh bukti baru memang mengubahnya.

## Output
Assumption ledger ringkas: asumsi, dampak jika salah, confidence, cara validasi, dan prioritas.
