"""Background workers used for PDF and HTML rendering."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import fitz
from PySide6.QtCore import QThread, Signal

from manual_builder.ai_service import ManualAIService, PdfStructurePlan
from manual_builder.html_service import HtmlRenderService, HtmlStructurePlan
from manual_builder.models import PdfPage
from manual_builder.pdf_service import PdfRenderService
from manual_builder.translation_service import ManusTranslationService


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

    @staticmethod
    def _pages_needing_visual_read(pages: list[PdfPage]) -> list[PdfPage]:
        """Identify PDF pages whose selectable text is too sparse for reliable analysis.

        A page can expose only a footer or page number while its actual technical content
        is rasterized. Such pages need visual reading before the structure is generated.
        """
        base_pages = [page for page in pages if page.variant == 1 and page.source_type == "pdf"]
        sparse_pages = [page for page in base_pages if len(page.extracted_text.strip()) < 350]
        if not base_pages or not sparse_pages:
            return []
        if len(sparse_pages) / len(base_pages) >= 0.35:
            return sparse_pages
        return sparse_pages[:8]

    @staticmethod
    def _sample_pages(pages: list[PdfPage], limit: int = 16) -> list[PdfPage]:
        """Keep visual requests bounded while covering the whole document."""
        if len(pages) <= limit:
            return pages
        last = len(pages) - 1
        indexes = {round(position * last / (limit - 1)) for position in range(limit)}
        return [page for index, page in enumerate(pages) if index in indexes]

    def _supplement_visual_text(self) -> int:
        """Use vision only when selectable PDF text is unavailable or materially incomplete."""
        candidates = self._sample_pages(self._pages_needing_visual_read(self._pages))
        if not candidates or not self._api_key.strip():
            return 0
        vision_service = ManusTranslationService(
            source_language="en",
            api_key=self._api_key,
            endpoint=self._base_url,
            model=self._model,
        )
        recovered = 0
        for page in candidates:
            visual_text = vision_service.extract_page_outline_text(page.image_path)
            if len(visual_text.strip()) >= 20:
                # A transcrição visual é somente uma evidência para a sugestão de estrutura.
                # Nunca sobrescreva ``extracted_text``: ele é o único texto que pode seguir
                # automaticamente para o R Markdown final.
                replacement = replace(page, visual_outline_text=visual_text.strip())
                page_index = self._pages.index(page)
                self._pages[page_index] = replacement
                recovered += 1
        return recovered

    def run(self) -> None:
        """Create an evidence-based structure without blocking the main interface."""
        try:
            recovered_pages = self._supplement_visual_text()
            service = ManualAIService(self._api_key, self._base_url, self._model)
            plan: PdfStructurePlan = service.create_pdf_structure(
                self._pages, self._manual_title
            )
            # Preserva exclusivamente o texto selecionável original para a montagem do
            # manual. Leitura visual de apoio permanece em ``visual_outline_text``.
            plan.extracted_text_by_page = {
                page.number: page.extracted_text
                for page in self._pages
                if page.extracted_text.strip()
            }
            if recovered_pages:
                prefix = (
                    f"Leitura visual aplicada a {recovered_pages} página(s) sem texto extraível. "
                )
                plan.note = prefix + (plan.note or "Estrutura criada a partir do conteúdo visível.")
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
