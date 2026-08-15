"""Antarmuka dasar BaseOCRExtractor."""

from abc import ABC, abstractmethod


class BaseOCRExtractor(ABC):
    """Antarmuka ekstraksi teks dari citra gambar."""

    @abstractmethod
    def extract_text_from_image(self, image_path: str) -> str | None:
        """Mengekstrak teks mentah dari file gambar."""
