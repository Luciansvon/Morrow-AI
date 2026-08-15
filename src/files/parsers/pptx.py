"""Parser dokumen Microsoft PowerPoint (.pptx)."""



class PPTXParser:
    """Parser untuk mengekstrak teks slide dan catatan dari berkas .pptx."""

    @staticmethod
    def parse_pptx(file_path: str) -> tuple[str | None, bool]:
        try:
            from pptx import Presentation
            prs = Presentation(file_path)
            slide_texts = []

            for idx, slide in enumerate(prs.slides, start=1):
                slide_content = [f"--- Slide {idx} ---"]
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text.strip():
                        slide_content.append(shape.text.strip())
                slide_texts.append("\n".join(slide_content))

            full_text = "\n\n".join(slide_texts).strip()
            return full_text if full_text else None, True
        except Exception as e:
            return f"Error parsing PPTX: {e!s}", False


pptx_parser = PPTXParser()
