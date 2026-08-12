"""Background worker for multilingual exports that may call remote AI services."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from manual_builder.models import ManualSection
from manual_builder.project_service import ProjectExportService


class MultilingualExportWorker(QThread):
    """Create language-specific projects without blocking the graphical interface."""

    progress_changed = Signal(int, int)
    completed = Signal(str)
    failed = Signal(str)

    def __init__(
        self,
        destination: Path,
        title: str,
        sections: list[ManualSection],
        manual_code: str,
        publication_date: str,
        languages: list[str],
        source_language: str,
        translation_provider: str,
        api_key: str,
        translation_endpoint: str,
        cover_image_path: Path | None = None,
    ) -> None:
        super().__init__()
        self._destination = destination
        self._title = title
        self._sections = sections
        self._manual_code = manual_code
        self._publication_date = publication_date
        self._languages = languages
        self._source_language = source_language
        self._translation_provider = translation_provider
        self._api_key = api_key
        self._translation_endpoint = translation_endpoint
        self._cover_image_path = cover_image_path

    def run(self) -> None:
        """Run the export service and forward progress to the UI thread."""
        try:
            project = ProjectExportService().export_multilingual(
                self._destination,
                self._title,
                self._sections,
                self._languages,
                self._source_language,
                self._translation_provider,
                self._api_key,
                self._translation_endpoint,
                self._manual_code,
                self._publication_date,
                self.progress_changed.emit,
                cover_image_path=self._cover_image_path,
            )
            self.completed.emit(str(project))
        except Exception as error:
            self.failed.emit(str(error))
