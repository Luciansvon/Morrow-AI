---
name: progress_review
description: Review status pekerjaan, timeline, deadline, keterlambatan, progres, dan laporan operasional singkat.
eligible_roles: [manager]
triggers: [status, progress, progres, update, deadline, terlambat, timeline, laporan status, weekly review]
---
## Tujuan
Mengubah status tersebar menjadi gambaran kerja yang menjawab: apa selesai, apa berubah, apa berisiko, dan apa berikutnya.

## Workflow
1. Gunakan status task/backend sebagai sumber keadaan, jangan menebak progress persen.
2. Kelompokkan done, in-progress, blocked/waiting, dan next.
3. Sorot perubahan sejak update sebelumnya hanya jika konteks menyediakannya.
4. Kaitkan risiko dengan deadline/dependency konkret.
5. Jangan mengklaim reminder atau kalender sudah diubah tanpa hasil backend + approval yang sesuai.

## Output
Ringkasan status, blocker/risiko, deadline relevan, dan next action dengan owner.
