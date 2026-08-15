"""Attachment intake dengan extension allowlist dan MIME consistency check."""

from pathlib import Path

from src.core.types import AttachmentInfo
from src.storage.attachments import attachment_storage
from src.storage.sqlite import db


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".csv", ".txt", ".md", ".pptx", ".png", ".jpg", ".jpeg", ".webp"}

ALLOWED_MIME = {
    ".pdf": {"application/pdf"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/zip"},
    ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/zip"},
    ".pptx": {"application/vnd.openxmlformats-officedocument.presentationml.presentation", "application/zip"},
    ".csv": {"text/csv", "text/plain", "application/octet-stream"},
    ".txt": {"text/plain", "application/octet-stream"},
    ".md": {"text/markdown", "text/plain", "application/octet-stream"},
    ".png": {"image/png"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".webp": {"image/webp"},
}


class FileIntakeService:
    @staticmethod
    def detect_mime_type(file_path: str, fallback_ext: str) -> str:
        mapping = {ext: next(iter(mimes)) for ext, mimes in ALLOWED_MIME.items()}
        try:
            import puremagic
            guessed = puremagic.from_file(file_path, mime=True)
            if guessed and "/" in guessed:
                return guessed
        except Exception:
            pass
        return mapping.get(fallback_ext.lower(), "application/octet-stream")

    @classmethod
    async def process_incoming_file(cls, filename: str, content: bytes) -> AttachmentInfo:
        ext = Path(filename).suffix.lower()
        extension_supported = ext in SUPPORTED_EXTENSIONS
        file_id, file_path, file_size = attachment_storage.save_file(filename, content)
        detected_mime = cls.detect_mime_type(file_path, ext)
        mime_ok = extension_supported and detected_mime in ALLOWED_MIME.get(ext, set())

        await db.execute(
            """INSERT OR REPLACE INTO attachments
               (id, file_id, original_name, detected_mime, file_path, file_size)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (file_id, file_id, Path(filename).name, detected_mime, file_path, file_size),
        )
        error = None
        if not extension_supported:
            error = f"Format '{ext or '(tanpa ekstensi)'}' tidak didukung."
        elif not mime_ok:
            error = f"Tipe file tidak konsisten: ekstensi {ext}, MIME terdeteksi {detected_mime}."
        return AttachmentInfo(
            file_id=file_id,
            original_name=Path(filename).name,
            detected_mime=detected_mime,
            file_path=file_path,
            file_size=file_size,
            is_supported=bool(extension_supported and mime_ok),
            error_message=error,
        )


file_intake = FileIntakeService()
