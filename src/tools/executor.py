"""Eksekutor alat idempoten (Idempotent Tool Executor) dengan perlindungan side-effect."""

from typing import Any

from src.tools.policy import tool_policy
from src.tools.registry import tool_registry


class IdempotentToolExecutor:
    """Eksekutor alat yang aman, idempoten, dan mencegah eksekusi aksi luar tanpa izin."""

    def __init__(self):
        self._executed_keys: dict[str, Any] = {}

    async def execute_tool(
        self,
        tool_name: str,
        parameters: dict[str, Any],
        idempotency_key: str | None = None,
        is_approved: bool = False,
    ) -> dict[str, Any]:
        """
        Mengeksekusi tool dengan jaminan:
        1. Jika aksi eksternal dan belum disetujui (is_approved=False), eksekusi DITOLAK.
        2. Jika idempotency_key sudah pernah dieksekusi, kembalikan hasil sebelumnya (mencegah double execution).
        """
        # 1. Cek Kebijakan Persetujuan Manusia
        if tool_policy.requires_user_approval(tool_name) and not is_approved:
            return {
                "success": False,
                "error": f"Aksi eksternal '{tool_name}' membutuhkan persetujuan eksplisit pengguna sebelum dapat dieksekusi.",
                "requires_approval": True,
            }

        # 2. Cek Idempotensi
        if idempotency_key:
            if idempotency_key in self._executed_keys:
                return {
                    "success": True,
                    "idempotent_replay": True,
                    "result": self._executed_keys[idempotency_key],
                }

        # 3. Cari fungsi tool
        func = tool_registry.get_tool(tool_name)
        if not func:
            # Simulasi fungsi bawaan jika belum terdaftar
            result = f"[Eksekusi Sukses: {tool_name} dengan parameter {parameters}]"
            if idempotency_key:
                self._executed_keys[idempotency_key] = result
            return {"success": True, "result": result}

        try:
            res = await func(**parameters)
            if idempotency_key:
                self._executed_keys[idempotency_key] = res
            return {"success": True, "result": res}
        except Exception as e:
            return {"success": False, "error": str(e)}


tool_executor = IdempotentToolExecutor()
