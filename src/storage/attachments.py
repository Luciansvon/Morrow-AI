"""Manajemen penyimpanan fisik berkas lampiran dengan proteksi sandboxing."""

import uuid
from pathlib import Path

from src.core.config import settings


class AttachmentStorage:
    def __init__(self, base_dir: str | None = None):
        self.base_dir = Path(base_dir or settings.storage_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def is_path_safe(self, target_path: Path) -> bool:
        """Memastikan path file berada di dalam sandbox base_dir (mencegah path traversal)."""
        try:
            resolved = target_path.resolve()
            return resolved.is_relative_to(self.base_dir)
        except (ValueError, RuntimeError):
            return False

    def save_file(self, filename: str, content: bytes) -> tuple[str, str, int]:
        """
        Menyimpan konten berkas ke folder sandbox.
        Mengembalikan (file_id, file_path_str, file_size_bytes).
        """
        size_bytes = len(content)
        max_bytes = settings.max_attachment_size_mb * 1024 * 1024
        if size_bytes > max_bytes:
            raise ValueError(f"Ukuran berkas ({size_bytes} bytes) melebihi batas {settings.max_attachment_size_mb} MB")

        file_id = f"file_{uuid.uuid4().hex[:12]}"
        safe_filename = Path(filename).name  # Hapus path traversal jika ada
        target_dir = self.base_dir / file_id
        target_dir.mkdir(parents=True, exist_ok=True)

        target_file = target_dir / safe_filename
        if not self.is_path_safe(target_file):
            raise PermissionError("Akses path di luar sandbox ditolak!")

        with open(target_file, "wb") as f:
            f.write(content)

        return file_id, str(target_file), size_bytes

    def get_file_path(self, file_id: str, filename: str) -> Path | None:
        target = self.base_dir / file_id / filename
        if target.exists() and self.is_path_safe(target):
            return target
        return None


# Helper instance
attachment_storage = AttachmentStorage()
