"""Attachment intake dengan allowlist, magic consistency, dan archive/image safety limits."""

import asyncio
import uuid
import zipfile
from pathlib import Path

from src.core.config import settings
from src.core.types import AttachmentInfo
from src.storage.attachments import attachment_storage
from src.storage.sqlite import db

SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".xlsx", ".csv", ".txt", ".md", ".pptx",
    ".png", ".jpg", ".jpeg", ".webp",
}
ALLOWED_MIME = {
    ".pdf": {"application/pdf"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",
    },
    ".xlsx": {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/zip",
    },
    ".pptx": {
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/zip",
    },
    ".csv": {"text/csv", "text/plain", "application/octet-stream"},
    ".txt": {"text/plain", "application/octet-stream"},
    ".md": {"text/markdown", "text/plain", "application/octet-stream"},
    ".png": {"image/png"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".webp": {"image/webp"},
}
OOXML_MARKERS = {
    ".docx": "word/document.xml",
    ".xlsx": "xl/workbook.xml",
    ".pptx": "ppt/presentation.xml",
}


class FileIntakeService:
    @staticmethod
    def _fallback_magic(file_path: str) -> str:
        with open(file_path, "rb") as handle:
            data = handle.read(4096)
        if data.startswith(b"%PDF-"):
            return "application/pdf"
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if data.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            return "image/webp"
        if data.startswith(b"PK\x03\x04"):
            return "application/zip"
        try:
            data.decode("utf-8")
            return "text/plain"
        except UnicodeDecodeError:
            return "application/octet-stream"

    @classmethod
    def detect_mime_type(cls, file_path: str, fallback_ext: str) -> str:
        del fallback_ext
        try:
            import puremagic

            guessed = puremagic.from_file(file_path, mime=True)
            if guessed and "/" in guessed:
                return guessed
        except Exception:
            pass
        return cls._fallback_magic(file_path)

    @staticmethod
    def _validate_ooxml_archive(file_path: str, ext: str) -> str | None:
        max_uncompressed = settings.max_archive_uncompressed_mb * 1024 * 1024
        try:
            with zipfile.ZipFile(file_path) as archive:
                infos = archive.infolist()
                if len(infos) > settings.max_archive_entries:
                    return (
                        f"Arsip Office memiliki terlalu banyak entri ({len(infos)} > "
                        f"{settings.max_archive_entries})."
                    )
                total_uncompressed = sum(max(0, item.file_size) for item in infos)
                if total_uncompressed > max_uncompressed:
                    return (
                        "Ukuran hasil ekstraksi arsip Office melebihi batas "
                        f"{settings.max_archive_uncompressed_mb} MB."
                    )
                names = set(archive.namelist())
                marker = OOXML_MARKERS[ext]
                if marker not in names:
                    return f"Struktur {ext} tidak valid: komponen '{marker}' tidak ditemukan."
        except (zipfile.BadZipFile, OSError, RuntimeError) as exc:
            return f"Arsip {ext} tidak valid: {exc}"
        return None

    @staticmethod
    def _validate_image(file_path: str) -> str | None:
        try:
            from PIL import Image

            with Image.open(file_path) as image:
                width, height = image.size
                if width <= 0 or height <= 0:
                    return "Dimensi gambar tidak valid."
                if width * height > settings.max_image_pixels:
                    return (
                        f"Resolusi gambar terlalu besar ({width}x{height}); batas "
                        f"{settings.max_image_pixels} piksel."
                    )
                image.verify()
        except Exception as exc:
            return f"Gambar tidak valid: {exc}"
        return None

    @staticmethod
    def _rejected(filename: str, content: bytes, error: str, mime: str = "application/octet-stream") -> AttachmentInfo:
        return AttachmentInfo(
            file_id=f"rejected_{uuid.uuid4().hex[:12]}",
            original_name=Path(filename).name or "attachment",
            detected_mime=mime,
            file_path="",
            file_size=len(content),
            is_supported=False,
            error_message=error,
        )

    @classmethod
    async def process_incoming_file(cls, filename: str, content: bytes) -> AttachmentInfo:
        ext = Path(filename).suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            return cls._rejected(
                filename,
                content,
                f"Format '{ext or '(tanpa ekstensi)'}' tidak didukung.",
            )

        max_bytes = settings.max_attachment_size_mb * 1024 * 1024
        if len(content) > max_bytes:
            return cls._rejected(
                filename,
                content,
                f"Ukuran berkas melebihi batas {settings.max_attachment_size_mb} MB.",
            )

        file_id, file_path, file_size = await asyncio.to_thread(attachment_storage.save_file, filename, content)
        detected_mime = await asyncio.to_thread(cls.detect_mime_type, file_path, ext)
        if detected_mime not in ALLOWED_MIME.get(ext, set()):
            await asyncio.to_thread(attachment_storage.remove_file, file_id)
            return cls._rejected(
                filename,
                content,
                f"Tipe file tidak konsisten: ekstensi {ext}, MIME terdeteksi {detected_mime}.",
                detected_mime,
            )

        validation_error = None
        if ext in OOXML_MARKERS:
            validation_error = await asyncio.to_thread(cls._validate_ooxml_archive, file_path, ext)
        elif ext in {".png", ".jpg", ".jpeg", ".webp"}:
            validation_error = await asyncio.to_thread(cls._validate_image, file_path)
        if validation_error:
            await asyncio.to_thread(attachment_storage.remove_file, file_id)
            return cls._rejected(filename, content, validation_error, detected_mime)

        await db.execute(
            """INSERT OR REPLACE INTO attachments
               (id, file_id, original_name, detected_mime, file_path, file_size)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (file_id, file_id, Path(filename).name, detected_mime, file_path, file_size),
        )
        return AttachmentInfo(
            file_id=file_id,
            original_name=Path(filename).name,
            detected_mime=detected_mime,
            file_path=file_path,
            file_size=file_size,
            is_supported=True,
        )


file_intake = FileIntakeService()
