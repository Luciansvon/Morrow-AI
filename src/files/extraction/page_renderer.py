"""Bounded PDF page renderer for OCR/vision fallback."""

import math
from pathlib import Path

from src.core.config import settings


class PageRenderer:
    @staticmethod
    def render_pdf_to_images(pdf_path: str, max_pages: int = 5) -> list[str]:
        image_paths: list[str] = []
        doc = None
        try:
            import fitz

            doc = fitz.open(pdf_path)
            base_name = Path(pdf_path).stem
            output_dir = Path(pdf_path).parent / "rendered_pages"
            output_dir.mkdir(parents=True, exist_ok=True)
            target_scale = 150 / 72

            for page_idx in range(min(len(doc), max_pages)):
                page = doc[page_idx]
                width_points = max(float(page.rect.width), 1.0)
                height_points = max(float(page.rect.height), 1.0)
                estimated_pixels = (
                    width_points
                    * height_points
                    * target_scale
                    * target_scale
                )
                scale = target_scale
                if estimated_pixels > settings.max_image_pixels:
                    scale *= math.sqrt(settings.max_image_pixels / estimated_pixels)
                pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                img_path = output_dir / f"{base_name}_page_{page_idx + 1}.png"
                pix.save(str(img_path))
                image_paths.append(str(img_path))
        except Exception as exc:
            for image_path in image_paths:
                Path(image_path).unlink(missing_ok=True)
            if image_paths:
                try:
                    Path(image_paths[0]).parent.rmdir()
                except OSError:
                    pass
            raise RuntimeError(f"Gagal merender PDF untuk OCR/vision: {exc}") from exc
        finally:
            if doc is not None:
                doc.close()
        return image_paths


page_renderer = PageRenderer()
