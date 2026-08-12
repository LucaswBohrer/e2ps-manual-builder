"""Main graphical window for E2PS Manual Builder."""

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
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from manual_builder.models import ManualSection, ManualSubsection, PdfPage
from manual_builder.ai_service import ManualAIService
from manual_builder.crop_dialog import CropDialog
from manual_builder.export_worker import MultilingualExportWorker
from manual_builder.project_service import ProjectExportService
from manual_builder.workers import PdfRenderWorker


class MainWindow(QMainWindow):
    """Main application window managing PDF extraction, sections, and multilingual export."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("E2PS Manual Builder (AI Powered)")
        self.resize(1300, 820)

        self._pages: list[PdfPage] = []
        self._sections: list[ManualSection] = []
        self._temp_dir = TemporaryDirectory(prefix="e2ps_manual_")
        self._render_worker: PdfRenderWorker | None = None
        self._export_worker: MultilingualExportWorker | None = None
        self._ai_service = ManualAIService()
        self._cover_image_path: Path | None = None

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

        # AI Assistant Button for automated structuring
        self.ai_suggest_button = QPushButton("🤖 AI Suggest Manual Structure")
        self.ai_suggest_button.setEnabled(False)
        self.ai_suggest_button.clicked.connect(self.ai_suggest_structure)

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

        # Text editing between images for selected section/subsection
        self.section_text_input = QTextEdit()
        self.section_text_input.setPlaceholderText("Descriptive or technical text to appear between/alongside images in this section...")
        self.section_text_input.setMaximumHeight(100)
        self.section_text_input.setEnabled(False)
        
        self.save_text_button = QPushButton("Save Section Text")
        self.save_text_button.setEnabled(False)
        self.save_text_button.clicked.connect(self.save_section_text)

        self.ai_generate_text_button = QPushButton("🤖 AI Generate Technical Text")
        self.ai_generate_text_button.setEnabled(False)
        self.ai_generate_text_button.clicked.connect(self.ai_generate_section_text)

        self.section_tree.currentItemChanged.connect(self._section_selection_changed)

        section_panel = QGroupBox("Manual Sections & AI Assistant")
        section_layout = QVBoxLayout(section_panel)
        section_layout.addWidget(self.ai_suggest_button)
        section_layout.addWidget(QLabel("1. Check pages in the left panel."))
        section_layout.addWidget(QLabel("2. Name the section."))
        section_layout.addWidget(self.section_name)
        section_layout.addWidget(self.add_section_button)
        section_layout.addWidget(QLabel("Sections to export:"))
        section_layout.addWidget(self.rename_section_button)
        section_layout.addWidget(self.subsection_name)
        section_layout.addWidget(self.add_subsection_button)
        section_layout.addWidget(self.section_tree)
        section_layout.addWidget(QLabel("Section Descriptive Text (between images):"))
        section_layout.addWidget(self.section_text_input)
        
        text_btn_layout = QHBoxLayout()
        text_btn_layout.addWidget(self.save_text_button)
        text_btn_layout.addWidget(self.ai_generate_text_button)
        section_layout.addLayout(text_btn_layout)
        
        section_layout.addWidget(self.remove_section_button)

        language_group = QGroupBox("Translation & Cover")
        language_layout = QVBoxLayout(language_group)
        language_layout.addWidget(QLabel("Source language:"))
        self.source_language = QComboBox()
        self.source_language.addItem("Portuguese", "pt")
        self.source_language.addItem("English", "en")
        self.source_language.addItem("Spanish", "es")
        language_layout.addWidget(self.source_language)
        language_layout.addWidget(QLabel("Create language folders:"))
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
        self.translation_provider.addItem("Manus AI (Free & Integrated)", "manus")
        language_layout.addWidget(self.translation_provider)
        self.translation_endpoint = QLineEdit("")
        self.translation_endpoint.setVisible(False)
        self.api_key_input = QLineEdit("")
        self.api_key_input.setVisible(False)

        language_layout.addWidget(QLabel("Manual Cover Image (Capa.png):"))
        cover_layout = QHBoxLayout()
        self.cover_path_input = QLineEdit()
        self.cover_path_input.setPlaceholderText("Select cover image (optional)...")
        self.cover_path_input.setReadOnly(True)
        cover_button = QPushButton("Browse...")
        cover_button.clicked.connect(self._browse_cover_image)
        cover_layout.addWidget(self.cover_path_input)
        cover_layout.addWidget(cover_button)
        language_layout.addLayout(cover_layout)

        section_layout.addWidget(language_group)
        self.preview = QLabel("Open a PDF to begin")
        self.preview.setObjectName("preview")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(540, 500)

        splitter = QSplitter()
        splitter.addWidget(page_panel)
        splitter.addWidget(section_panel)
        splitter.addWidget(self.preview)
        splitter.setSizes([260, 420, 620])
        self.setCentralWidget(splitter)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.statusBar().addPermanentWidget(self.progress)

    def open_pdf(self) -> None:
        """Open a PDF file and start background rendering."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open PDF Manual", "", "PDF Documents (*.pdf)"
        )
        if not file_path:
            return
        self._pages.clear()
        self._sections.clear()
        self.page_list.clear()
        self.section_tree.clear()
        self.export_button.setEnabled(False)
        self.select_all_button.setEnabled(False)
        self.clear_selection_button.setEnabled(False)
        self.crop_page_button.setEnabled(False)
        self.ai_suggest_button.setEnabled(False)

        self._render_worker = PdfRenderWorker(Path(file_path), Path(self._temp_dir.name))
        self._render_worker.progress_changed.connect(self._update_render_progress)
        self._render_worker.page_rendered.connect(self._page_rendered)
        self._render_worker.completed.connect(self._rendering_completed)
        self._render_worker.failed.connect(self._rendering_failed)

        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setVisible(True)
        self._render_worker.start()
        self.statusBar().showMessage("Rendering PDF pages...")

    def _update_render_progress(self, percent: int) -> None:
        self.progress.setValue(percent)

    def _page_rendered(self, page: PdfPage) -> None:
        self._pages.append(page)
        item = QListWidgetItem(page.display_name)
        item.setData(Qt.ItemDataRole.UserRole, page)
        item.setCheckState(Qt.CheckState.Unchecked)
        item.setIcon(QIcon(str(page.thumbnail_path)))
        item.setSizeHint(QSize(0, 42))
        self.page_list.addItem(item)

    def _rendering_completed(self, total: int) -> None:
        self.progress.setVisible(False)
        self.select_all_button.setEnabled(True)
        self.clear_selection_button.setEnabled(True)
        self.crop_page_button.setEnabled(True)
        self.ai_suggest_button.setEnabled(bool(self._pages))
        self.statusBar().showMessage(f"Successfully rendered {total} pages")

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
        """Validate input and start multilingual background export."""
        languages = self._selected_languages()
        if not languages:
            QMessageBox.warning(self, "Languages required", "Select at least one output language.")
            return
        if not self._sections:
            QMessageBox.warning(self, "Sections required", "Create at least one section before exporting.")
            return

        source_language = self.source_language.currentData()
        destination = QFileDialog.getExistingDirectory(self, "Choose project location")
        if not destination:
            return
        cover_path = getattr(self, "_cover_image_path", None)
        self._export_worker = MultilingualExportWorker(
            Path(destination),
            self.title_input.text().strip(),
            self._sections,
            self.code_input.text().strip(),
            self._publication_date(),
            languages,
            source_language,
            "manus",
            "",
            "",
            cover_image_path=cover_path,
        )
        self._export_worker.progress_changed.connect(self._update_export_progress)
        self._export_worker.completed.connect(self._export_finished)
        self._export_worker.failed.connect(self._export_failed)
        self.progress.setRange(0, 0)
        self.progress.setVisible(True)
        self.export_button.setEnabled(False)
        self._export_worker.start()
        self.statusBar().showMessage("Exporting language projects and translating pages with Manus AI…")

    def add_section(self) -> None:
        """Create a named section from currently checked page items."""
        title = self.section_name.text().strip()
        pages = self._checked_pages()
        if not title:
            QMessageBox.warning(self, "Section name required", "Enter a title for the section.")
            return
        self._sections.append(ManualSection(title=title, pages=pages))
        self.section_name.clear()
        self.deselect_all_pages()
        self._refresh_sections()
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
        self.section_text_input.clear()
        self.section_text_input.setEnabled(False)
        self.save_text_button.setEnabled(False)
        self.ai_generate_text_button.setEnabled(False)

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
        page = item.data(Qt.ItemDataRole.UserRole)
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
        """Enable section actions and load section text when an item is selected."""
        has_selection = current is not None
        self.remove_section_button.setEnabled(has_selection)
        self.rename_section_button.setEnabled(has_selection)
        self.add_subsection_button.setEnabled(has_selection)
        self.section_text_input.setEnabled(has_selection)
        self.save_text_button.setEnabled(has_selection)
        self.ai_generate_text_button.setEnabled(has_selection)

        if current is not None:
            item_type, section_index, subsection_index = current.data(0, Qt.ItemDataRole.UserRole)
            if item_type == "section":
                self.section_text_input.setPlainText(self._sections[section_index].text_content)
            else:
                self.section_text_input.setPlainText(self._sections[section_index].subsections[subsection_index].text_content)
        else:
            self.section_text_input.clear()

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

    def save_section_text(self) -> None:
        """Save text content for the currently selected section or subsection."""
        item = self.section_tree.currentItem()
        if item is None:
            return
        text = self.section_text_input.toPlainText()
        item_type, section_index, subsection_index = item.data(0, Qt.ItemDataRole.UserRole)
        if item_type == "section":
            self._sections[section_index].text_content = text
        else:
            self._sections[section_index].subsections[subsection_index].text_content = text
        self.statusBar().showMessage("Section descriptive text saved successfully.")

    def ai_suggest_structure(self) -> None:
        """Use Manus AI to automatically suggest manual sections and page allocation."""
        if not self._pages:
            QMessageBox.warning(self, "No pages", "Open a PDF first.")
            return
        
        self.statusBar().showMessage("Manus AI is analyzing pages and structuring the manual...")
        self.progress.setRange(0, 0)
        self.progress.setVisible(True)
        self.ai_suggest_button.setEnabled(False)

        try:
            suggested = self._ai_service.suggest_structure(self._pages, self.title_input.text().strip())
            if suggested:
                self._sections = suggested
                self._refresh_sections()
                self.export_button.setEnabled(True)
                QMessageBox.information(
                    self,
                    "AI Structure Applied",
                    f"Manus AI successfully structured the manual into {len(suggested)} main sections with descriptive text!",
                )
        except Exception as error:
            QMessageBox.critical(self, "AI Error", f"Could not generate structure: {error}")
        finally:
            self.progress.setVisible(False)
            self.ai_suggest_button.setEnabled(True)
            self.statusBar().showMessage("AI structure suggestion complete")

    def ai_generate_section_text(self) -> None:
        """Use Manus AI to generate professional technical text for the selected section."""
        item = self.section_tree.currentItem()
        if item is None:
            QMessageBox.warning(self, "Select Section", "Choose a section or subsection first.")
            return
        
        item_type, section_index, subsection_index = item.data(0, Qt.ItemDataRole.UserRole)
        title = (
            self._sections[section_index].title
            if item_type == "section"
            else self._sections[section_index].subsections[subsection_index].title
        )

        self.statusBar().showMessage(f"Generating technical text for '{title}' via Manus AI...")
        try:
            generated = self._ai_service.generate_section_text(title, self.title_input.text().strip())
            self.section_text_input.setPlainText(generated)
            self.save_section_text()
            QMessageBox.information(self, "AI Text Generated", f"Technical text generated successfully for '{title}'!")
        except Exception as error:
            QMessageBox.critical(self, "AI Error", f"Could not generate text: {error}")
        finally:
            self.statusBar().showMessage("Ready")

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

    def _browse_cover_image(self) -> None:
        """Open a file dialog to select the manual cover image."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Manual Cover Image",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp)",
        )
        if file_path:
            self._cover_image_path = Path(file_path)
            self.cover_path_input.setText(self._cover_image_path.name)
            self.statusBar().showMessage(f"Cover image selected: {self._cover_image_path.name}")
