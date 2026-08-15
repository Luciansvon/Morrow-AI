"""Intake berkas lampiran, deteksi format via magic bytes, dan validasi keamanan."""

from pathlib import Path

from src.core.types import AttachmentInfo
from src.storage.attachments import attachment_storage
from src.storage.sqlite import db

# Format yang didukung resmi MVP PRD v0.2
SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".xlsx", ".csv", ".txt", ".md", ".pptx",
    ".png", ".jpg", ".jpeg", ".webp"
}


class FileIntakeService:
    """Layanan penerimaan dan validasi berkas lampiran."""

    @staticmethod
    def detect_mime_type(file_path: str, fallback_ext: str) -> str:
        """Mendeteksi tipe MIME sebenarnya menggunakan magic bytes."""
        ext = fallback_ext.lower()
        mapping = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ".csv": "text/csv",
            ".txt": "text/plain",
            ".md": "text/markdown",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
        }

        try:
            import puremagic
            guessed = puremagic.from_file(file_path, mime=True)
            if guessed and "/" in guessed:
                return guessed
        except Exception:
            pass

        return mapping.get(ext, "application/octet-stream")

    @classmethod
    async def process_incoming_file(
        cls,
        filename: str,
        content: bytes,
    ) -> AttachmentInfo:
        """
        Menyimpan berkas secara aman, mendeteksi format asli, dan mencatat ke database.
        """
        ext = Path(filename).suffix.lower()
        is_supported = ext in SUPPORTED_EXTENSIONS

        # Simpan fisik file ke sandboxed storage
        file_id, file_path_str, file_size = attachment_storage.save_file(filename, content)
        detected_mime = cls.detect_mime_type(file_path_str, ext)

        # Catat metadata ke database
        await db.execute(
            """
            INSERT OR REPLACE INTO attachments (id, file_id, original_name, detected_mime, file_path, file_size)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (file_id, file_id, filename, detected_mime, file_path_str, file_size),
        )

        return AttachmentInfo(
            file_id=file_id,
            original_name=filename,
            detected_mime=detected_mime,
            file_path=file_path_str,
            file_size=file_size,
            is_supported=is_supported,
        )


file_intake = FileIntakeService()
