"""Penyalur pesan semantik menggunakan model MiMo-V2.5 (Role Router)."""

import json

from src.core.types import NormalizedMessage, RoleID
from src.llm.model_catalog import MODEL_CATALOG
from src.llm.openrouter import openrouter_client
from src.routing.fast_path import fast_path_router

ROUTER_SYSTEM_PROMPT = """Anda adalah Penyalur Pesan Utama (Role Router) untuk tim AI Morrow.
Tugas Anda adalah menganalisis pesan pengguna dan lampiran berkas (jika ada), lalu memilih TEPAT SATU agen penanggung jawab utama:

Daftar Peran:
- 'manager': Koordinasi tim, perencanaan tugas, penjadwalan, pelacakan dependensi, dan manajemen operasional.
- 'marketing': Strategi kampanye promosi, riset pasar, pembuatan materi konten, copywriting, dan analisis data pemasaran.
- 'advisor': Analisis risiko bisnis, pertimbangan untung-rugi (trade-offs), keputusan strategis jangka panjang, dan evaluasi dampak.

Format Output WAJIB JSON:
{"owner": "manager" | "marketing" | "advisor", "confidence": float, "reason": "alasan singkat"}
"""


class RoleRouter:
    """Penyalur pesan cerdas dengan prinsip Fast Path ➡️ Semantic Fallback."""

    @staticmethod
    async def route_message(message: NormalizedMessage) -> tuple[RoleID, str]:
        # 1. Coba jalur cepat deterministik terlebih dahulu
        fast_result = await fast_path_router.resolve_fast_path(message)
        if fast_result:
            return fast_result

        # 2. Jika ambigu, gunakan Semantic Router via MiMo-V2.5 Non-Thinking
        file_contexts = []
        for att in message.attachments:
            summary = f"[Lampiran: {att.original_name} ({att.detected_mime})]"
            if att.extracted_text:
                summary += f"\nIsi Teks Ekstraksi:\n{att.extracted_text[:400]}"
            if att.visual_description:
                summary += f"\nDeskripsi Visual: {att.visual_description}"
            file_contexts.append(summary)

        full_user_content = message.text
        if file_contexts:
            full_user_content += "\n\n" + "\n".join(file_contexts)

        messages = [
            {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
            {"role": "user", "content": full_user_content},
        ]

        try:
            res = await openrouter_client.chat_completion(
                messages=messages,
                model=MODEL_CATALOG["mimo_v2_5"].model_id,
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            data = json.loads(res.content)
            owner_str = data.get("owner", "manager").lower()
            reason = data.get("reason", "Semantic intent classification")

            if owner_str in ("manager", "marketing", "advisor"):
                return RoleID(owner_str), f"Router Semantik: {reason}"
        except Exception:
            pass

        # Default fallback jika semua gagal: serahkan ke Manager
        return RoleID.MANAGER, "Default fallback ke Manager"


role_router = RoleRouter()
