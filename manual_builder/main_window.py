"""Main desktop window and user interaction orchestration."""

from __future__ import annotations

from datetime import date
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QIcon, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QComboBox,
    QCheckBox,
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
    QTreeWidget,
    QTreeWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from manual_builder.models import ManualSection, ManualSubsection, PdfPage
from manual_builder.crop_dialog import CropDialog
from manual_builder.export_worker import MultilingualExportWorker
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
        self._export_worker: MultilingualExportWorker | None = None
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
        self.crop_page_button = QPushButton("Create Crop Copy")
        self.crop_page_button.setEnabled(False)
        self.crop_page_button.clicked.connect(self.crop_current_page)
        page_panel = QGroupBox("PDF Pages")
        page_layout = QVBoxLayout(page_panel)
        page_layout.addWidget(self.select_all_button)
        page_layout.addWidget(self.clear_selection_button)
        page_layout.addWidget(self.crop_page_button)
        page_layout.addWidget(self.page_list)
        self.section_name = QLineEdit()
        self.section_name.setPlaceholderText("Section name, e.g. Installation")
        self.add_section_button = QPushButton("Create Section from Checked Pages")
        self.add_section_button.setEnabled(False)
        self.add_section_button.clicked.connect(self.add_section)
        self.section_tree = QTreeWidget()
        self.section_tree.setHeaderHidden(True)
        self.remove_section_button = QPushButton("Remove Selected Section")
        self.remove_section_button.setEnabled(False)
        self.remove_section_button.clicked.connect(self.remove_selected_section)
        self.rename_section_button = QPushButton("Rename Selected Item")
        self.rename_section_button.setEnabled(False)
        self.rename_section_button.clicked.connect(self.rename_selected_item)
        self.subsection_name = QLineEdit()
        self.subsection_name.setPlaceholderText("Subsection name")
        self.add_subsection_button = QPushButton("Add Subsection to Selected Section")
        self.add_subsection_button.setEnabled(False)
        self.add_subsection_button.clicked.connect(self.add_subsection)
        self.section_tree.currentItemChanged.connect(self._section_selection_changed)

        section_panel = QGroupBox("Manual Sections")
        section_layout = QVBoxLayout(section_panel)
        section_layout.addWidget(QLabel("1. Check pages in the left panel."))
        section_layout.addWidget(QLabel("2. Name the section."))
        section_layout.addWidget(self.section_name)
        section_layout.addWidget(self.add_section_button)
        section_layout.addWidget(QLabel("Sections to export:"))
        section_layout.addWidget(self.rename_section_button)
        section_layout.addWidget(self.subsection_name)
        section_layout.addWidget(self.add_subsection_button)
        section_layout.addWidget(self.section_tree)
        section_layout.addWidget(self.remove_section_button)
        language_group = QGroupBox("Translation Output")
        language_layout = QVBoxLayout(language_group)
        language_layout.addWidget(QLabel("Source language:"))
        self.source_language = QComboBox()
        self.source_language.addItem("Portuguese", "pt")
        self.source_language.addItem("English", "en")
        self.source_language.addItem("Spanish", "es")
        language_layout.addWidget(self.source_language)
        language_layout.addWidget(QLabel("Create language folders (up to 3):"))
        self.pt_language = QCheckBox("Portuguese (pt)")
        self.en_language = QCheckBox("English (en)")
        self.es_language = QCheckBox("Spanish (es)")
        self.pt_language.setChecked(True)
        self.en_language.setChecked(True)
        language_layout.addWidget(self.pt_language)
        language_layout.addWidget(self.en_language)
        language_layout.addWidget(self.es_language)
        language_layout.addWidget(QLabel("Translation provider:"))
        self.translation_provider = QComboBox()
        self.translation_provider.addItem("MyMemory (Free API, zero config)", "mymemory")
        self.translation_provider.addItem("LibreTranslate (free text translation)", "libretranslate")
        self.translation_provider.addItem("OpenAI (visual page translation)", "openai")
        language_layout.addWidget(self.translation_provider)
        language_layout.addWidget(QLabel("Translation endpoint (LibreTranslate):"))
        self.translation_endpoint = QLineEdit("http://localhost:5000/translate")
        language_layout.addWidget(self.translation_endpoint)
        language_layout.addWidget(QLabel("OpenAI API key (only for visual translation):"))
        self.api_key_input = QLineEdit(os.getenv("OPENAI_API_KEY", ""))
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("sk-...")
        language_layout.addWidget(self.api_key_input)
        section_layout.addWidget(language_group)
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
        self.section_tree.clear()
        self.preview.setText("Rendering pages…")
        self.progress.setRange(0, 0)
        self.progress.setVisible(True)
        self.export_button.setEnabled(False)
        self.add_section_button.setEnabled(False)
        self.select_all_button.setEnabled(False)
        self.clear_selection_button.setEnabled(False)
        self.crop_page_button.setEnabled(False)
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
            item = QListWidgetItem(page.display_name)
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
        self.crop_page_button.setEnabled(bool(pages))
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
        page = item.data(0, Qt.ItemDataRole.UserRole)
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
        languages = self._selected_languages()
        if not languages:
            QMessageBox.warning(
                self,
                "No languages selected",
                "Choose at least one output language.",
            )
            return
        source_language = self.source_language.currentData()
        api_key = self.api_key_input.text().strip()
        provider = self.translation_provider.currentData()
        endpoint = self.translation_endpoint.text().strip()
        needs_translation = any(language != source_language for language in languages)
        if provider == "openai" and needs_translation and not api_key:
            QMessageBox.warning(
                self,
                "OpenAI API key required",
                "Enter an API key to translate pages into another language.",
            )
            return
        if provider == "libretranslate" and needs_translation and not endpoint:
            QMessageBox.warning(
                self,
                "Translation endpoint required",
                "Enter the URL of a LibreTranslate-compatible endpoint.",
            )
            return
        if provider == "libretranslate" and needs_translation:
            QMessageBox.information(
                self,
                "Free translation limitation",
                "LibreTranslate translates the manual title and section names. "
                "It does not redraw text inside page images; those PNGs are copied "
                "unchanged.",
            )
        destination = QFileDialog.getExistingDirectory(self, "Choose project location")
        if not destination:
            return
        self._export_worker = MultilingualExportWorker(
            Path(destination),
            self.title_input.text().strip(),
            self._sections,
            self.code_input.text().strip(),
            self._publication_date(),
            languages,
            source_language,
            provider,
            api_key,
            endpoint,
        )
        self._export_worker.progress_changed.connect(self._update_export_progress)
        self._export_worker.completed.connect(self._export_finished)
        self._export_worker.failed.connect(self._export_failed)
        self.progress.setRange(0, 0)
        self.progress.setVisible(True)
        self.export_button.setEnabled(False)
        self._export_worker.start()
        self.statusBar().showMessage("Exporting language projects and translating pages…")

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

        self._sections.append(ManualSection(title=title, pages=pages, subsections=[]))
        self._refresh_sections()
        for index in range(self.page_list.count()):
            self.page_list.item(index).setCheckState(Qt.CheckState.Unchecked)
        self.section_name.clear()
        self.export_button.setEnabled(True)
        self.statusBar().showMessage(f"Section '{title}' created with {len(pages)} pages")

    def remove_selected_section(self) -> None:
        """Remove the selected section without deleting rendered pages."""
        item = self.section_tree.currentItem()
        if item is None:
            return
        item_type, section_index, subsection_index = item.data(0, Qt.ItemDataRole.UserRole)
        if item_type == "section":
            self._sections.pop(section_index)
        else:
            self._sections[section_index].subsections.pop(subsection_index)
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

    def crop_current_page(self) -> None:
        """Open a visual crop editor for the currently selected PDF page."""
        item = self.page_list.currentItem()
        if item is None:
            QMessageBox.warning(self, "Select a page", "Choose a page to crop first.")
            return
        page = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(page, PdfPage):
            return
        source = QPixmap(str(page.image_path))
        if source.isNull():
            QMessageBox.critical(self, "Image error", "The selected page image could not be opened.")
            return
        dialog = CropDialog(source, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        cropped = source.copy(dialog.selected_rect())
        next_variant = max(
            existing.variant for existing in self._pages if existing.number == page.number
        ) + 1
        image_path = page.image_path.with_name(
            f"page_{page.number:03d}_crop_{next_variant:02d}.png"
        )
        thumbnail_path = page.thumbnail_path.with_name(
            f"thumbnail_{page.number:03d}_crop_{next_variant:02d}.png"
        )
        if not cropped.save(str(image_path), "PNG"):
            QMessageBox.critical(self, "Crop error", "The cropped image could not be saved.")
            return
        thumbnail = cropped.scaled(
            QSize(150, 150),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        thumbnail.save(str(thumbnail_path), "PNG")
        crop_page = PdfPage(page.number, image_path, thumbnail_path, next_variant)
        self._pages.append(crop_page)
        crop_item = QListWidgetItem(crop_page.display_name)
        crop_item.setData(Qt.ItemDataRole.UserRole, crop_page)
        crop_item.setCheckState(Qt.CheckState.Unchecked)
        crop_item.setIcon(QIcon(str(crop_page.thumbnail_path)))
        crop_item.setSizeHint(QSize(0, 42))
        self.page_list.insertItem(self.page_list.row(item) + 1, crop_item)
        self.page_list.setCurrentItem(crop_item)
        self.statusBar().showMessage(f"Created crop {next_variant:02d} from page {page.number}")

    def _refresh_sections(self) -> None:
        """Refresh the compact section summary shown in the UI."""
        self.section_tree.clear()
        for index, section in enumerate(self._sections, start=1):
            page_labels = ", ".join(page.display_name for page in section.pages)
            parent = QTreeWidgetItem([f"{index}. {section.title} ({page_labels})"])
            parent.setData(0, Qt.ItemDataRole.UserRole, ("section", index - 1, -1))
            self.section_tree.addTopLevelItem(parent)
            for sub_index, subsection in enumerate(section.subsections, start=1):
                sub_pages = ", ".join(page.display_name for page in subsection.pages)
                child = QTreeWidgetItem([f"{sub_index}. {subsection.title} ({sub_pages})"])
                child.setData(
                    0,
                    Qt.ItemDataRole.UserRole,
                    ("subsection", index - 1, sub_index - 1),
                )
                parent.addChild(child)
            parent.setExpanded(True)

    def _section_selection_changed(
        self,
        current: QTreeWidgetItem | None,
        previous: QTreeWidgetItem | None,
    ) -> None:
        """Enable section actions only when an item in the structure is selected."""
        has_selection = current is not None
        self.remove_section_button.setEnabled(has_selection)
        self.rename_section_button.setEnabled(has_selection)
        self.add_subsection_button.setEnabled(has_selection)

    def rename_selected_item(self) -> None:
        """Rename the selected section or subsection using the section-name field."""
        title = self.section_name.text().strip()
        item = self.section_tree.currentItem()
        if not title or item is None:
            QMessageBox.warning(self, "Name required", "Enter a new name before renaming.")
            return
        item_type, section_index, subsection_index = item.data(0, Qt.ItemDataRole.UserRole)
        if item_type == "section":
            self._sections[section_index].title = title
        else:
            self._sections[section_index].subsections[subsection_index].title = title
        self.section_name.clear()
        self._refresh_sections()

    def add_subsection(self) -> None:
        """Create a subsection under the selected section from checked pages."""
        title = self.subsection_name.text().strip()
        pages = self._checked_pages()
        item = self.section_tree.currentItem()
        if not title or not pages or item is None:
            QMessageBox.warning(
                self,
                "Subsection details required",
                "Select a section, enter a subsection name, and check its pages.",
            )
            return
        _, section_index, _ = item.data(0, Qt.ItemDataRole.UserRole)
        self._sections[section_index].subsections.append(
            ManualSubsection(title=title, pages=pages)
        )
        self.subsection_name.clear()
        self.deselect_all_pages()
        self._refresh_sections()

    def _publication_date(self) -> str:
        """Return the E2PS publication date based on selected year and semester."""
        return f"{self.year_input.currentText()}-{self.semester_input.currentData()}"

    def _selected_languages(self) -> list[str]:
        """Return selected output language codes in display order."""
        controls = (
            ("pt", self.pt_language),
            ("en", self.en_language),
            ("es", self.es_language),
        )
        return [code for code, control in controls if control.isChecked()]

    def _update_export_progress(self, current: int, total: int) -> None:
        """Show multilingual export progress, including remote translations."""
        self.progress.setRange(0, total)
        self.progress.setValue(current)

    def _export_finished(self, project: str) -> None:
        """Present the completed language project directory to the user."""
        self.progress.setVisible(False)
        self.export_button.setEnabled(bool(self._sections))
        QMessageBox.information(self, "Projects created", f"Language projects created at:\n{project}")
        self.statusBar().showMessage("Multilingual export completed")

    def _export_failed(self, error: str) -> None:
        """Restore the UI when an AI translation or export operation fails."""
        self.progress.setVisible(False)
        self.export_button.setEnabled(bool(self._sections))
        QMessageBox.critical(self, "Export failed", error)
        self.statusBar().showMessage("Multilingual export failed")
