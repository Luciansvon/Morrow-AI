"""Optional local OCR. Ketidaktersediaan Tesseract tidak dipalsukan sebagai hasil OCR."""

from src.files.ocr.base import BaseOCRExtractor


class LocalOCRExtractor(BaseOCRExtractor):
    def extract_text_from_image(self, image_path: str) -> str | None:
        try:
            from PIL import Image

            with Image.open(image_path) as image:
                try:
                    import pytesseract

                    text = pytesseract.image_to_string(image)
                    return text.strip() or None
                except (ImportError, OSError, RuntimeError):
                    return None
        except Exception:
            return None


local_ocr = LocalOCRExtractor()
