"""Renderer halaman PDF ke format gambar (PNG) untuk jalur OCR."""

from pathlib import Path


class PageRenderer:
    """Merender halaman dokumen PDF menjadi kumpulan gambar."""

    @staticmethod
    def render_pdf_to_images(pdf_path: str, max_pages: int = 5) -> list[str]:
        """
        Merender halaman PDF menjadi file gambar PNG.
        Mengembalikan daftar path berkas gambar yang dihasilkan.
        """
        image_paths = []
        try:
            import fitz
            doc = fitz.open(pdf_path)
            base_name = Path(pdf_path).stem
            output_dir = Path(pdf_path).parent / "rendered_pages"
            output_dir.mkdir(parents=True, exist_ok=True)

            for page_idx in range(min(len(doc), max_pages)):
                page = doc[page_idx]
                pix = page.get_pixmap(dpi=150)
                img_path = output_dir / f"{base_name}_page_{page_idx+1}.png"
                pix.save(str(img_path))
                image_paths.append(str(img_path))

            doc.close()
        except Exception:
            pass
        return image_paths


page_renderer = PageRenderer()
