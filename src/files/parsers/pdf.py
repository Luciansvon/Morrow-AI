"""Parser dokumen PDF berbasis text layer (PyMuPDF / pypdf)."""

from src.core.config import settings


class PDFParser:
    @staticmethod
    def _join_bounded(parts: list[str]) -> str:
        return "\n".join(parts)[: settings.max_document_extract_chars].strip()

    @staticmethod
    def parse_pdf(file_path: str) -> tuple[str | None, bool]:
        limit = settings.max_document_extract_chars
        try:
            import fitz

            text_content: list[str] = []
            total_chars = 0
            doc = fitz.open(file_path)
            try:
                for page in doc:
                    text = page.get_text()
                    if text:
                        remaining = max(0, limit - total_chars)
                        text_content.append(text[:remaining])
                        total_chars += min(len(text), remaining)
                    if total_chars >= limit:
                        break
            finally:
                doc.close()
            full_text = PDFParser._join_bounded(text_content)
            return full_text if full_text else None, total_chars >= 20
        except Exception:
            pass

        try:
            import pypdf

            text_content = []
            total_chars = 0
            reader = pypdf.PdfReader(file_path)
            for page in reader.pages:
                text = page.extract_text() or ""
                if text:
                    remaining = max(0, limit - total_chars)
                    text_content.append(text[:remaining])
                    total_chars += min(len(text), remaining)
                if total_chars >= limit:
                    break
            full_text = PDFParser._join_bounded(text_content)
            return full_text if full_text else None, total_chars >= 20
        except Exception:
            return None, False


pdf_parser = PDFParser()
