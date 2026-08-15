"""Pendeteksi konflik instruksi pengguna (Human Instruction Conflict Detector)."""


from src.core.types import TaskModel, TaskStatus


class ConflictDetector:
    """Mendeteksi pertentangan instruksi antar pengguna / tugas aktif (CAP-SAFETY)."""

    @staticmethod
    def detect_conflict(
        new_instruction: str,
        active_tasks: list[TaskModel],
    ) -> tuple[bool, str | None, TaskModel | None]:
        """
        Memeriksa apakah instruksi baru bertentangan dengan tugas yang sedang berjalan.
        Jika ya, mengembalikan (is_conflict, conflict_description, affected_task).
        """
        text_lower = new_instruction.lower()

        # Contoh pola pertentangan langsung (batal vs lanjutkan, ganti total)
        conflict_keywords = ["batalkan", "jangan jadi", "batal", "ubah total", "tunda semua"]

        for task in active_tasks:
            # Jika ada instruksi pembatalan/perubahan drastis saat tugas sedang in_progress
            if task.status == TaskStatus.IN_PROGRESS:
                for kw in conflict_keywords:
                    if kw in text_lower:
                        desc = f"Instruksi baru '{new_instruction}' berpotensi membatalkan/mengubah tugas aktif '{task.title}'"
                        return True, desc, task

        return False, None, None


conflict_detector = ConflictDetector()
