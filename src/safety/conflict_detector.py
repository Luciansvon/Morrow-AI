"""Pendeteksi konflik instruksi pengguna (Human Instruction Conflict Detector)."""

import re

from src.core.types import TaskModel, TaskStatus


class ConflictDetector:
    """Mendeteksi pertentangan instruksi antar pengguna / tugas aktif (CAP-SAFETY)."""

    CONFLICT_KEYWORDS = ("batalkan", "jangan jadi", "batal", "ubah total", "tunda semua")
    GENERIC_TITLE_TOKENS = {
        "buat", "bikin", "luncurkan", "kerjakan", "task", "tugas", "rencana",
        "proyek", "project", "untuk", "yang", "dan", "dengan", "sekarang",
    }

    @classmethod
    def _target_score(cls, instruction: str, task: TaskModel) -> int:
        instruction_tokens = set(re.findall(r"[a-z0-9]+", instruction.lower()))
        title_tokens = {
            token
            for token in re.findall(r"[a-z0-9]+", task.title.lower())
            if len(token) >= 3 and token not in cls.GENERIC_TITLE_TOKENS
        }
        return len(instruction_tokens & title_tokens)

    @classmethod
    def detect_conflict(
        cls,
        new_instruction: str,
        active_tasks: list[TaskModel],
    ) -> tuple[bool, str | None, TaskModel | None]:
        """Deteksi konflik tanpa memilih task secara arbitrer saat target ambigu."""
        text_lower = new_instruction.lower()
        if not any(keyword in text_lower for keyword in cls.CONFLICT_KEYWORDS):
            return False, None, None

        in_progress = [task for task in active_tasks if task.status == TaskStatus.IN_PROGRESS]
        if not in_progress:
            return False, None, None

        if len(in_progress) == 1:
            task = in_progress[0]
            desc = (
                f"Instruksi baru '{new_instruction}' berpotensi membatalkan/mengubah "
                f"tugas aktif '{task.title}'"
            )
            return True, desc, task

        scored = [(cls._target_score(new_instruction, task), task) for task in in_progress]
        best_score = max(score for score, _ in scored)
        best_matches = [task for score, task in scored if score == best_score and score > 0]
        if len(best_matches) == 1:
            task = best_matches[0]
            desc = (
                f"Instruksi baru '{new_instruction}' berpotensi membatalkan/mengubah "
                f"tugas aktif '{task.title}'"
            )
            return True, desc, task

        titles = ", ".join(f"'{task.title}'" for task in in_progress[:5])
        desc = (
            "Instruksi pembatalan/perubahan ambigu karena ada beberapa task aktif: "
            f"{titles}. Sebutkan task yang dimaksud sebelum otomatisasi dilanjutkan."
        )
        return True, desc, None


conflict_detector = ConflictDetector()
