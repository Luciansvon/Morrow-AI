---
name: recommendation_synthesis
description: Menyusun rekomendasi akhir, membandingkan opsi, menjawab 'sebaiknya apa', dan menetapkan kondisi keputusan.
eligible_roles: [advisor]
triggers: [rekomendasi, recommend, recommendation, saran, sebaiknya, keputusan akhir, pilih mana]
---
## Tujuan
Mengubah analisis menjadi keputusan yang dapat dipahami dan ditindaklanjuti tanpa menyembunyikan dissent atau uncertainty.

## Workflow
1. Nyatakan objective dan decision criteria.
2. Bandingkan opsi pada kriteria yang sama.
3. Identifikasi opsi dominan, trade-off yang tersisa, dan informasi yang paling bernilai untuk dicari.
4. Pilih rekomendasi jika bukti cukup; bila tidak, berikan rekomendasi kondisional.
5. Catat dissent/risiko penting yang tidak boleh hilang hanya demi ringkasan rapi.

## Output
Rekomendasi satu kalimat, alasan utama, trade-off, confidence, kondisi pembatal/ubah, dan next validation.
