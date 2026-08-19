---
name: task_coordination
description: Koordinasi pekerjaan, pemecahan task, owner, dependensi, jadwal, roadmap, dan delegasi internal.
eligible_roles: [manager]
triggers: [task, tugas, proyek, project, plan, rencana, jadwal, roadmap, sprint]
tools: []
---
## Tujuan
Ubah permintaan kerja menjadi rencana yang dapat dijalankan tanpa mengambil alih domain spesialis.

## Workflow
1. Nyatakan outcome dan batasan yang benar-benar diketahui.
2. Pecah pekerjaan menjadi task secukupnya; hindari mikro-task tanpa nilai.
3. Tentukan owner tunggal, dependensi, urutan, dan status yang masuk akal.
4. Delegasikan pekerjaan Marketing/Advisor ke role tersebut melalui mekanisme backend, bukan lewat klaim teks.
5. Jangan mengklaim `create_task`, `delegate_task`, atau `update_task_status` sebagai tool LLM sampai fungsi tersebut benar-benar terdaftar di ToolRegistry.
6. Jika tindakan keluar Morrow diperlukan, berhenti di proposal tindakan dan approval.

## Output
Berikan rencana ringkas dengan owner, dependensi, urutan, blocker, dan next action.
