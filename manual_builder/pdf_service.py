"""PDF rendering service, intentionally independent from UI code."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable

import fitz

from manual_builder.models import PdfPage


class PdfRenderService:
    """Render PDF pages as PNG images using PyMuPDF."""

    EXPORT_DPI = 200
    THUMBNAIL_SCALE = 0.25

    def render(
        self,
        source: Path,
        destination: Path,
        on_progress: Callable[[int, int], None],
    ) -> list[PdfPage]:
        """Render all pages and report completed pages through a callback."""
        destination.mkdir(parents=True, exist_ok=True)
        pages: list[PdfPage] = []
        document = fitz.open(source)
        try:
            total = len(document)
            for index, page in enumerate(document, start=1):
                export_pixmap = page.get_pixmap(dpi=self.EXPORT_DPI, alpha=False)
                image_path = destination / f"page_{index:03d}.png"
                export_pixmap.save(image_path)
                thumbnail_pixmap = page.get_pixmap(
                    matrix=fitz.Matrix(self.THUMBNAIL_SCALE, self.THUMBNAIL_SCALE),
                    alpha=False,
                )
                thumbnail_path = destination / f"thumbnail_{index:03d}.png"
                thumbnail_pixmap.save(thumbnail_path)
                pages.append(
                    PdfPage(
                        number=index,
                        image_path=image_path,
                        thumbnail_path=thumbnail_path,
                    )
                )
                on_progress(index, total)
        finally:
            document.close()
        return pages
