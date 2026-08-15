"""Kebijakan eksekusi alat (Internal Otomatis vs Eksternal Wajib Izin User)."""


# Kumpulan aksi yang berdampak ke dunia luar dan WAJIB meminta izin user (CAP-APPROVAL)
EXTERNAL_ACTIONS: set[str] = {
    "send_email",
    "send_external_message",
    "modify_calendar",
    "post_social_media",
    "execute_transaction",
    "modify_external_account",
    "destructive_external_write",
}


class ToolPolicy:
    """Pemeriksa batasan otoritas eksekusi alat."""

    @staticmethod
    def requires_user_approval(action_type: str) -> bool:
        """Mengembalikan True jika aksi membutuhkan persetujuan eksplisit manusia."""
        return action_type in EXTERNAL_ACTIONS

    @staticmethod
    def is_internal_action(action_type: str) -> bool:
        """Mengembalikan True jika aksi bersifat internal dan boleh jalan otomatis."""
        return not ToolPolicy.requires_user_approval(action_type)


tool_policy = ToolPolicy()
