"""Manajemen penyimpanan fisik berkas lampiran dengan proteksi sandboxing."""

import shutil
import uuid
from pathlib import Path

from src.core.config import settings


class AttachmentStorage:
    def __init__(self, base_dir: str | None = None):
        self._base_dir_override = Path(base_dir).resolve() if base_dir else None

    @property
    def base_dir(self) -> Path:
        """Resolve storage lazily so runtime/test config changes are respected."""
        base = self._base_dir_override or Path(settings.storage_dir).resolve()
        base.mkdir(parents=True, exist_ok=True)
        return base

    def is_path_safe(self, target_path: Path) -> bool:
        """Memastikan path file berada di dalam sandbox base_dir."""
        try:
            return target_path.resolve().is_relative_to(self.base_dir)
        except (ValueError, RuntimeError):
            return False

    def save_file(self, filename: str, content: bytes) -> tuple[str, str, int]:
        """Simpan berkas dan kembalikan ``(file_id, path, size_bytes)``."""
        size_bytes = len(content)
        max_bytes = settings.max_attachment_size_mb * 1024 * 1024
        if size_bytes > max_bytes:
            raise ValueError(
                f"Ukuran berkas ({size_bytes} bytes) melebihi batas "
                f"{settings.max_attachment_size_mb} MB"
            )

        file_id = f"file_{uuid.uuid4().hex[:12]}"
        safe_filename = Path(filename).name.strip() or "attachment.bin"
        target_dir = self.base_dir / file_id
        target_file = target_dir / safe_filename
        if not self.is_path_safe(target_file):
            raise PermissionError("Akses path di luar sandbox ditolak!")

        target_dir.mkdir(parents=True, exist_ok=False)
        target_file.write_bytes(content)
        return file_id, str(target_file), size_bytes

    def remove_file(self, file_id: str) -> None:
        """Best-effort removal of one attachment sandbox directory."""
        target_dir = self.base_dir / file_id
        if target_dir.exists() and self.is_path_safe(target_dir):
            shutil.rmtree(target_dir, ignore_errors=True)

    def get_file_path(self, file_id: str, filename: str) -> Path | None:
        target = self.base_dir / file_id / Path(filename).name
        if target.exists() and self.is_path_safe(target):
            return target
        return None


attachment_storage = AttachmentStorage()
