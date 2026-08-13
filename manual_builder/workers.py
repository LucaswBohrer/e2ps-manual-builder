"""Background workers used for PDF and HTML rendering."""

from __future__ import annotations

from pathlib import Path

import fitz
from PySide6.QtCore import QThread, Signal

from manual_builder.ai_service import ManualAIService, PdfStructurePlan
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


class PdfStructureWorker(QThread):
    """Analyze extracted PDF text in the background and return a compact E2PS outline."""

    completed = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        pages: list[PdfPage],
        manual_title: str,
        api_key: str,
        base_url: str,
        model: str,
    ) -> None:
        super().__init__()
        self._pages = list(pages)
        self._manual_title = manual_title
        self._api_key = api_key
        self._base_url = base_url
        self._model = model

    def run(self) -> None:
        """Create a selection-focused structure, falling back safely when IA is unavailable."""
        try:
            service = ManualAIService(self._api_key, self._base_url, self._model)
            plan: PdfStructurePlan = service.create_pdf_structure(
                self._pages, self._manual_title
            )
            self.completed.emit(plan)
        except Exception as error:
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
