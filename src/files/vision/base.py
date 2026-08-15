"""Antarmuka dasar BaseVisionAnalyzer."""

from abc import ABC, abstractmethod


class BaseVisionAnalyzer(ABC):
    """Antarmuka pemahaman semantik visual gambar (bukan sekadar OCR teks)."""

    @abstractmethod
    async def analyze_visual(self, image_path: str, prompt: str = "") -> str | None:
        """Menganalisis komposisi, estetika, dan konteks semantik gambar."""
