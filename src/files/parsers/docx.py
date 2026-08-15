"""Parser dokumen Microsoft Word (.docx)."""



class DocxParser:
    """Parser untuk mengekstrak paragraf dan tabel dari file .docx."""

    @staticmethod
    def parse_docx(file_path: str) -> tuple[str | None, bool]:
        try:
            import docx
            doc = docx.Document(file_path)
            content_parts = []

            for p in doc.paragraphs:
                if p.text.strip():
                    content_parts.append(p.text)

            for table in doc.tables:
                for row in table.rows:
                    row_text = [c.text.strip() for c in row.cells]
                    if any(row_text):
                        content_parts.append(" | ".join(row_text))

            full_text = "\n".join(content_parts).strip()
            return full_text if full_text else None, True
        except Exception as e:
            return f"Error parsing DOCX: {e!s}", False


docx_parser = DocxParser()
