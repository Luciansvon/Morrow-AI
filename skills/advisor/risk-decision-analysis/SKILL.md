---
name: risk_decision_analysis
description: Analisis keputusan, risiko, trade-off, kontrak/legal/finansial, dampak, dan mitigasi berbasis bukti.
eligible_roles: [advisor]
triggers: [risiko, risk, keputusan, trade-off, legal, hukum, finansial, kontrak]
tools: []
---
## Tujuan
Membantu pengguna mengambil keputusan dengan trade-off dan ketidakpastian yang terlihat.

## Workflow
1. Nyatakan keputusan yang sebenarnya harus dibuat dan opsi realistis.
2. Pisahkan fakta, asumsi, inferensi, dan unknown.
3. Nilai tiap opsi pada outcome, downside, reversibility, timing, dependency, dan risiko.
4. Jangan mengklaim `evaluate_risk` atau `propose_decision` sebagai tool LLM sampai fungsi tersebut benar-benar terdaftar di ToolRegistry.
5. Jangan memberi kepastian palsu pada domain legal/finansial; tandai kebutuhan verifikasi profesional bila dampaknya material.
6. Berikan rekomendasi bersyarat bila bukti belum cukup.

## Output
Decision frame, opsi, trade-off, risk/mitigation, confidence, rekomendasi, dan kondisi yang dapat mengubah keputusan.
