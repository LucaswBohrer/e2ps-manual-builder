"""Background worker threads for non-blocking UI rendering and export."""

from __future__ import annotations

from pathlib import Path

import fitz
from PySide6.QtCore import QThread, Signal

from manual_builder.models import PdfPage
from manual_builder.pdf_service import PdfRenderService


class PdfRenderWorker(QThread):
    """Render a PDF in a dedicated Qt thread."""

    progress_changed = Signal(int, int)
    completed = Signal(list)
    failed = Signal(str)

    def __init__(self, source: Path, destination: Path) -> None:
        super().__init__()
        self._source = source
        self._destination = destination

    def run(self) -> None:
        """Execute rendering and send results back to the main thread."""
        try:
            pages: list[PdfPage] = PdfRenderService().render(
                self._source,
                self._destination,
                self.progress_changed.emit,
            )
            self.completed.emit(pages)
        except (OSError, RuntimeError, fitz.FileDataError) as error:
            self.failed.emit(str(error))
