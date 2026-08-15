---
name: dependency_recovery
description: Menangani task blocked, dependency macet, retry, blocker, dan jalur pemulihan tanpa loop tak terbatas.
eligible_roles: [manager]
triggers: [blocked, blocker, hambatan, ketergantungan, dependency, dependensi, stuck, macet, retry, gagal]
---
## Tujuan
Memulihkan pekerjaan yang terblokir dengan percobaan yang terbatas dan dapat diaudit.

## Workflow
1. Nyatakan blocker spesifik dan bukti yang ada.
2. Bedakan blocker internal, dependency role lain, dan dependency eksternal.
3. Cari alternatif urutan/dependency sebelum menambah retry.
4. Hormati retry budget dan attempted-agent chain backend; jangan menyarankan loop kembali ke owner yang sudah dicoba.
5. Dependency eksternal yang membutuhkan side effect harus berhenti untuk approval.

## Output
Blocker → opsi pemulihan → owner → batas retry/escalation → kondisi selesai.
