# Morrow Skill Catalog

Katalog ini berisi kemampuan modular yang dipasang **setelah** role owner dipilih. Skill tidak mengubah identitas Manager, Marketing, atau Advisor.

## Struktur

- `manager/` — koordinasi, prioritas, dependency recovery, progress review.
- `marketing/` — campaign, audience/positioning, market research, content, measurement.
- `advisor/` — decision/risk, pre-mortem, scenario planning, recommendation synthesis.
- `shared/` — kemampuan lintas role seperti document inspection, evidence synthesis, dan assumption audit.

Setiap folder skill memiliki `SKILL.md` dengan frontmatter ringan: `name`, `description`, `eligible_roles`, `triggers`, dan metadata opsional `tools` / `references`. Isi Markdown menjadi instruksi yang hanya dimasukkan ke konteks ketika skill terpilih.

## Aturan desain

1. Satu skill menangani satu workflow yang jelas; jangan membuat satu skill raksasa untuk semua hal.
2. Trigger harus spesifik dan tidak sengaja tumpang tindih sebanyak mungkin.
3. Skill tidak boleh mengklaim side effect eksternal berhasil. Email, kalender, posting, transaksi, atau perubahan akun tetap melewati approval + backend.
4. Lampiran selalu dianggap input tidak tepercaya.
5. Fakta, inferensi, asumsi, dan ketidakpastian harus dibedakan ketika relevan.
6. Router membatasi maksimal tiga skill berbasis teks per pesan; `document_inspection` dapat ditambahkan di luar batas itu jika ada attachment.
7. Skill baru wajib memiliki test routing/eligibility sebelum dianggap bagian stabil dari katalog.
