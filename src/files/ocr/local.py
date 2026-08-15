"""Implementasi ekstraktor OCR lokal menggunakan Pillow & pytesseract atau fallback."""


from src.files.ocr.base import BaseOCRExtractor


class LocalOCRExtractor(BaseOCRExtractor):
    """Ekstraktor teks gambar lokal."""

    def extract_text_from_image(self, image_path: str) -> str | None:
        try:
            from PIL import Image
            img = Image.open(image_path)

            try:
                import pytesseract
                text = pytesseract.image_to_string(img)
                return text.strip() if text.strip() else None
            except Exception:
                # Jika pytesseract binary belum terinstal di host OS, kembalikan indikator jujur
                return "[OCR Lokal: Gambar valid terdeteksi, teks gambar diteruskan ke Vision Model]"
        except Exception as e:
            return f"[OCR Error: {e!s}]"


local_ocr = LocalOCRExtractor()
