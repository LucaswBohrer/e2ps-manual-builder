"""Background workers used for PDF and HTML rendering."""

from __future__ import annotations

from pathlib import Path

import fitz
from PySide6.QtCore import QThread, Signal

from manual_builder.html_service import HtmlRenderService, HtmlStructurePlan
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


class HtmlRenderWorker(QThread):
    """Render a static HTML manual and analyze its semantic structure in the background."""

    progress_changed = Signal(int, int)
    completed = Signal(list, object)
    failed = Signal(str)

    def __init__(self, source: Path, destination: Path) -> None:
        super().__init__()
        self._source = source
        self._destination = destination

    def run(self) -> None:
        """Return visual pages and an outline inferred from the source headings and images."""
        try:
            service = HtmlRenderService()
            pages: list[PdfPage] = service.render(
                self._source,
                self._destination,
                self.progress_changed.emit,
            )
            plan: HtmlStructurePlan = service.analyze_structure(self._source)
            self.completed.emit(pages, plan)
        except (OSError, RuntimeError, ValueError) as error:
            self.failed.emit(str(error))
