"""Parser dokumen PDF berbasis text layer (PyMuPDF / fitz & pypdf)."""



class PDFParser:
    """Parser untuk mengekstrak teks struktural dari dokumen PDF."""

    @staticmethod
    def parse_pdf(file_path: str) -> tuple[str | None, bool]:
        """
        Mengekstrak teks dari PDF jika memiliki text layer yang valid.
        Mengembalikan (extracted_text, has_text_layer).
        """
        text_content = []
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(file_path)
            total_chars = 0
            for page in doc:
                text = page.get_text()
                total_chars += len(text.strip())
                text_content.append(text)
            doc.close()

            # Jika total karakter sangat sedikit (< 20 karakter per halaman), kemungkinan hasil scan
            has_text_layer = total_chars >= 20
            full_text = "\n".join(text_content).strip()
            return full_text if full_text else None, has_text_layer
        except Exception:
            pass

        # Fallback ke pypdf
        try:
            import pypdf
            reader = pypdf.PdfReader(file_path)
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    text_content.append(t)
            full_text = "\n".join(text_content).strip()
            return full_text if full_text else None, len(full_text) >= 20
        except Exception:
            return None, False


pdf_parser = PDFParser()
