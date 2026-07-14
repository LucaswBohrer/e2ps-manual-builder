"""Main desktop window and user interaction orchestration."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QIcon, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QComboBox,
    QGroupBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from manual_builder.models import ManualSection, PdfPage
from manual_builder.project_service import ProjectExportService
from manual_builder.workers import PdfRenderWorker


class MainWindow(QMainWindow):
    """E2PS Manual Builder primary user interface."""

    def __init__(self) -> None:
        super().__init__()
        self._temporary_images = TemporaryDirectory(prefix="e2ps_manual_")
        self._pages: list[PdfPage] = []
        self._sections: list[ManualSection] = []
        self._worker: PdfRenderWorker | None = None
        self.setWindowTitle("E2PS Manual Builder")
        self.resize(1180, 760)
        self._build_ui()

    def _build_ui(self) -> None:
        toolbar = QToolBar("Actions")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        open_action = QAction("Open PDF", self)
        open_action.triggered.connect(self.open_pdf)
        toolbar.addAction(open_action)
        toolbar.addSeparator()
        toolbar.addWidget(QLabel("Manual title:"))
        self.title_input = QLineEdit("E2PS Technical Manual")
        self.title_input.setMinimumWidth(280)
        toolbar.addWidget(self.title_input)
        toolbar.addSeparator()
        toolbar.addWidget(QLabel("Code:"))
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("e.g. 04945")
        self.code_input.setMaximumWidth(120)
        toolbar.addWidget(self.code_input)
        toolbar.addSeparator()
        today = date.today()
        toolbar.addWidget(QLabel("Year:"))
        self.year_input = QComboBox()
        for year in range(today.year - 2, today.year + 6):
            self.year_input.addItem(str(year))
        self.year_input.setCurrentText(str(today.year))
        toolbar.addWidget(self.year_input)
        toolbar.addWidget(QLabel("Semester:"))
        self.semester_input = QComboBox()
        self.semester_input.addItem("1st semester", "01")
        self.semester_input.addItem("2nd semester", "02")
        self.semester_input.setCurrentIndex(0 if today.month <= 6 else 1)
        toolbar.addWidget(self.semester_input)
        toolbar.addSeparator()
        self.export_button = QPushButton("Export Project")
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self.export_project)
        toolbar.addWidget(self.export_button)

        self.page_list = QListWidget()
        self.page_list.setMinimumWidth(245)
        self.page_list.currentItemChanged.connect(self._show_current_page)
        self.select_all_button = QPushButton("Select All Pages")
        self.select_all_button.setEnabled(False)
        self.select_all_button.clicked.connect(self.select_all_pages)
        self.clear_selection_button = QPushButton("Deselect All Pages")
        self.clear_selection_button.setEnabled(False)
        self.clear_selection_button.clicked.connect(self.deselect_all_pages)
        page_panel = QGroupBox("PDF Pages")
        page_layout = QVBoxLayout(page_panel)
        page_layout.addWidget(self.select_all_button)
        page_layout.addWidget(self.clear_selection_button)
        page_layout.addWidget(self.page_list)
        self.section_name = QLineEdit()
        self.section_name.setPlaceholderText("Section name, e.g. Installation")
        self.add_section_button = QPushButton("Create Section from Checked Pages")
        self.add_section_button.setEnabled(False)
        self.add_section_button.clicked.connect(self.add_section)
        self.section_list = QListWidget()
        self.remove_section_button = QPushButton("Remove Selected Section")
        self.remove_section_button.setEnabled(False)
        self.remove_section_button.clicked.connect(self.remove_selected_section)
        self.section_list.currentRowChanged.connect(
            lambda row: self.remove_section_button.setEnabled(row >= 0)
        )

        section_panel = QGroupBox("Manual Sections")
        section_layout = QVBoxLayout(section_panel)
        section_layout.addWidget(QLabel("1. Check pages in the left panel."))
        section_layout.addWidget(QLabel("2. Name the section."))
        section_layout.addWidget(self.section_name)
        section_layout.addWidget(self.add_section_button)
        section_layout.addWidget(QLabel("Sections to export:"))
        section_layout.addWidget(self.section_list)
        section_layout.addWidget(self.remove_section_button)
        self.preview = QLabel("Open a PDF to begin")
        self.preview.setObjectName("preview")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(540, 500)

        splitter = QSplitter()
        splitter.addWidget(page_panel)
        splitter.addWidget(section_panel)
        splitter.addWidget(self.preview)
        splitter.setStretchFactor(2, 1)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.statusBar().showMessage("Ready")
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(splitter)
        layout.addWidget(self.progress)
        self.setCentralWidget(container)

    def open_pdf(self) -> None:
        """Ask the user for a PDF and begin thumbnail rendering."""
        filename, _ = QFileDialog.getOpenFileName(self, "Open PDF", "", "PDF files (*.pdf)")
        if not filename:
            return
        self.page_list.clear()
        self._pages.clear()
        self._sections.clear()
        self.section_list.clear()
        self.preview.setText("Rendering pages…")
        self.progress.setRange(0, 0)
        self.progress.setVisible(True)
        self.export_button.setEnabled(False)
        self.add_section_button.setEnabled(False)
        self.select_all_button.setEnabled(False)
        self.clear_selection_button.setEnabled(False)
        image_dir = Path(self._temporary_images.name) / "pages"
        self._worker = PdfRenderWorker(Path(filename), image_dir)
        self._worker.progress_changed.connect(self._update_progress)
        self._worker.completed.connect(self._rendering_finished)
        self._worker.failed.connect(self._rendering_failed)
        self._worker.start()
        self.statusBar().showMessage("Rendering PDF…")

    def _update_progress(self, current: int, total: int) -> None:
        self.progress.setRange(0, total)
        self.progress.setValue(current)

    def _rendering_finished(self, pages: list[PdfPage]) -> None:
        self._pages = pages
        for page in pages:
            item = QListWidgetItem(f"Page {page.number:03d}")
            item.setData(Qt.ItemDataRole.UserRole, page)
            item.setCheckState(Qt.CheckState.Checked)
            item.setIcon(QIcon(str(page.thumbnail_path)))
            item.setSizeHint(QSize(0, 42))
            self.page_list.addItem(item)
        self.progress.setVisible(False)
        self.export_button.setEnabled(bool(pages))
        self.add_section_button.setEnabled(bool(pages))
        self.select_all_button.setEnabled(bool(pages))
        self.clear_selection_button.setEnabled(bool(pages))
        if pages:
            self.page_list.setCurrentRow(0)
        self.statusBar().showMessage(
            f"{len(pages)} pages ready. Check pages and create sections."
        )

    def _rendering_failed(self, error: str) -> None:
        self.progress.setVisible(False)
        self.preview.setText("Could not render this PDF")
        QMessageBox.critical(self, "PDF error", f"The PDF could not be opened.\n\n{error}")
        self.statusBar().showMessage("Rendering failed")

    def _show_current_page(self, item: QListWidgetItem | None) -> None:
        if item is None:
            return
        page = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(page, PdfPage):
            return
        pixmap = QPixmap(str(page.image_path))
        self.preview.setPixmap(pixmap.scaled(
            self.preview.size(), Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ))

    def export_project(self) -> None:
        """Export the selected pages into a new R Markdown project."""
        if not self._sections:
            QMessageBox.warning(
                self,
                "No sections created",
                "Create at least one section with checked pages before exporting.",
            )
            return
        destination = QFileDialog.getExistingDirectory(self, "Choose project location")
        if not destination:
            return
        project = ProjectExportService().export(
            Path(destination),
            self.title_input.text().strip(),
            self._sections,
            self.code_input.text().strip(),
            self._publication_date(),
        )
        QMessageBox.information(self, "Project created", f"Project created at:\n{project}")
        page_count = sum(len(section.pages) for section in self._sections)
        self.statusBar().showMessage(
            f"Exported {page_count} pages in {len(self._sections)} sections"
        )

    def add_section(self) -> None:
        """Create a named section from currently checked page items."""
        title = self.section_name.text().strip()
        pages = self._checked_pages()
        if not title:
            QMessageBox.warning(self, "Section name required", "Enter a section name.")
            return
        if not pages:
            QMessageBox.warning(
                self,
                "No pages checked",
                "Check one or more pages for this section.",
            )
            return

        selected_numbers = {page.number for page in pages}
        for section in self._sections:
            section.pages = [
                page for page in section.pages if page.number not in selected_numbers
            ]
        self._sections = [section for section in self._sections if section.pages]
        self._sections.append(ManualSection(title=title, pages=pages))
        self._refresh_sections()
        for index in range(self.page_list.count()):
            self.page_list.item(index).setCheckState(Qt.CheckState.Unchecked)
        self.section_name.clear()
        self.export_button.setEnabled(True)
        self.statusBar().showMessage(f"Section '{title}' created with {len(pages)} pages")

    def remove_selected_section(self) -> None:
        """Remove the selected section without deleting rendered pages."""
        row = self.section_list.currentRow()
        if row < 0:
            return
        self._sections.pop(row)
        self._refresh_sections()
        self.export_button.setEnabled(bool(self._sections))

    def _checked_pages(self) -> list[PdfPage]:
        """Return pages checked in the source page list, in PDF order."""
        return [
            self.page_list.item(index).data(Qt.ItemDataRole.UserRole)
            for index in range(self.page_list.count())
            if self.page_list.item(index).checkState() == Qt.CheckState.Checked
        ]

    def select_all_pages(self) -> None:
        """Mark every rendered PDF page for a bulk section assignment."""
        self._set_all_page_checks(Qt.CheckState.Checked)

    def deselect_all_pages(self) -> None:
        """Clear every page check without altering already created sections."""
        self._set_all_page_checks(Qt.CheckState.Unchecked)

    def _set_all_page_checks(self, state: Qt.CheckState) -> None:
        """Set a shared check state on every page item."""
        for index in range(self.page_list.count()):
            self.page_list.item(index).setCheckState(state)

    def _refresh_sections(self) -> None:
        """Refresh the compact section summary shown in the UI."""
        self.section_list.clear()
        for index, section in enumerate(self._sections, start=1):
            page_labels = ", ".join(str(page.number) for page in section.pages)
            self.section_list.addItem(
                f"{index}. {section.title} ({page_labels})"
            )

    def _publication_date(self) -> str:
        """Return the E2PS publication date based on selected year and semester."""
        return f"{self.year_input.currentText()}-{self.semester_input.currentData()}"
