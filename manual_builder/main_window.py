"""Main application window managing PDF extraction, sections, and multilingual export."""

from __future__ import annotations

from datetime import date
from html import escape
import os
from pathlib import Path
from tempfile import TemporaryDirectory
try:
    from PIL import Image
except ImportError:
    Image = None

from PySide6.QtCore import Qt, QSize, QSettings
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
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from manual_builder.models import ManualSection, ManualSubsection, PdfPage
from manual_builder.ai_service import ManualAIService, PdfStructurePlan
from manual_builder.content_editor_dialog import ContentEditorDialog
from manual_builder.crop_dialog import CropDialog
from manual_builder.export_worker import MultilingualExportWorker
from manual_builder.html_service import HtmlStructurePlan
from manual_builder.project_service import ProjectExportService
from manual_builder.project_file_service import ProjectFileService
from manual_builder.workers import HtmlRenderWorker, PdfRenderWorker, PdfStructureWorker


class MainWindow(QMainWindow):
    """Main application window managing PDF extraction, sections, and multilingual export."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("E2PS Manual Builder (AI Powered)")
        self.resize(1400, 850)

        self._pages: list[PdfPage] = []
        self._sections: list[ManualSection] = []
        self._temp_dir = TemporaryDirectory(prefix="e2ps_manual_")
        self._render_worker: PdfRenderWorker | None = None
        self._html_render_worker: HtmlRenderWorker | None = None
        self._pdf_structure_worker: PdfStructureWorker | None = None
        self._export_worker: MultilingualExportWorker | None = None
        self._ai_service = ManualAIService()
        self._cover_image_path: Path | None = None
        self._project_path: Path | None = None
        self._project_files = ProjectFileService()
        self._settings = QSettings("E2PS", "ManualBuilder")

        toolbar = QToolBar("Actions")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        open_action = QAction("Open PDF", self)
        open_action.triggered.connect(self.open_pdf)
        toolbar.addAction(open_action)
        
        open_html_action = QAction("Open HTML", self)
        open_html_action.triggered.connect(self.open_html)
        toolbar.addAction(open_html_action)

        open_images_action = QAction("Open Images", self)
        open_images_action.triggered.connect(self.open_images)
        toolbar.addAction(open_images_action)

        open_project_action = QAction("Open Project (.e2ps)", self)
        open_project_action.triggered.connect(self.open_e2ps_project)
        toolbar.addAction(open_project_action)

        self.save_project_action = QAction("Save Project (.e2ps)", self)
        self.save_project_action.setEnabled(False)
        self.save_project_action.triggered.connect(self.save_e2ps_project)
        toolbar.addAction(self.save_project_action)
        toolbar.addSeparator()
        toolbar.addWidget(QLabel("Manual title:"))
        self.title_input = QLineEdit("E2PS Technical Manual")
        self.title_input.setMinimumWidth(250)
        toolbar.addWidget(self.title_input)
        toolbar.addSeparator()
        toolbar.addWidget(QLabel("Code:"))
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("e.g. 04945")
        self.code_input.setMaximumWidth(100)
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
        self.semester_input.addItem("1st", "01")
        self.semester_input.addItem("2nd", "02")
        self.semester_input.setCurrentIndex(0 if today.month <= 6 else 1)
        toolbar.addWidget(self.semester_input)
        toolbar.addSeparator()
        self.export_button = QPushButton("Export Project")
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self.export_project)
        toolbar.addWidget(self.export_button)

        # Left panel: PDF Pages
        self.page_list = QListWidget()
        self.page_list.setMinimumWidth(230)
        self.page_list.currentItemChanged.connect(self._show_current_page)
        self.select_all_button = QPushButton("Select All")
        self.select_all_button.setEnabled(False)
        self.select_all_button.clicked.connect(self.select_all_pages)
        self.clear_selection_button = QPushButton("Deselect All")
        self.clear_selection_button.setEnabled(False)
        self.clear_selection_button.clicked.connect(self.deselect_all_pages)
        self.crop_page_button = QPushButton("Crop Selected Page")
        self.crop_page_button.setEnabled(False)
        self.crop_page_button.clicked.connect(self.crop_current_page)

        self.export_mode_combo = QComboBox()
        self.export_mode_combo.addItem("Modo: Imagem Traduzida", "image")
        self.export_mode_combo.addItem("Modo: Texto/Tabela (OCR)", "text")
        self.export_mode_combo.setToolTip("Escolha como esta página será exportada no manual final.")
        self.export_mode_combo.setEnabled(False)
        self.export_mode_combo.currentIndexChanged.connect(self._change_page_export_mode)
        
        page_panel = QGroupBox("Páginas, HTML e Recortes")
        page_layout = QVBoxLayout(page_panel)
        page_layout.addWidget(self.select_all_button)
        page_layout.addWidget(self.clear_selection_button)
        page_layout.addWidget(self.crop_page_button)
        page_layout.addWidget(QLabel("Exportar página selecionada como:"))
        page_layout.addWidget(self.export_mode_combo)
        page_layout.addWidget(self.page_list)

        # Middle panel: Sections, Subsections & Mixed Content Blocks
        self.ai_suggest_button = QPushButton("🤖 AI: Suggest Structure & Pages")
        self.ai_suggest_button.setEnabled(False)
        self.ai_suggest_button.clicked.connect(self.ai_suggest_structure)

        self.section_name = QLineEdit()
        self.section_name.setPlaceholderText("Section name, e.g. 1. Instalação")
        self.add_section_button = QPushButton("Create Section (Checked Pages)")
        self.add_section_button.setEnabled(False)
        self.add_section_button.clicked.connect(self.add_section)
        
        self.section_tree = QTreeWidget()
        self.section_tree.setHeaderHidden(True)
        self.remove_section_button = QPushButton("Remove Selected")
        self.remove_section_button.setEnabled(False)
        self.remove_section_button.clicked.connect(self.remove_selected_section)
        self.rename_section_button = QPushButton("Rename Selected")
        self.rename_section_button.setEnabled(False)
        self.rename_section_button.clicked.connect(self.rename_selected_item)
        self.edit_content_button = QPushButton("Editar Conteúdo Selecionado")
        self.edit_content_button.setEnabled(False)
        self.edit_content_button.clicked.connect(self.edit_selected_content)
        
        self.subsection_name = QLineEdit()
        self.subsection_name.setPlaceholderText("Subsection name")
        self.add_subsection_button = QPushButton("Add Subsection (Checked Pages)")
        self.add_subsection_button.setEnabled(False)
        self.add_subsection_button.clicked.connect(self.add_subsection)

        # Flexible content insertion (Text block or Page block)
        self.content_text_input = QTextEdit()
        self.content_text_input.setPlaceholderText("Escreva aqui texto técnico/descritivo para inserir no manual...")
        self.content_text_input.setMaximumHeight(80)
        self.content_text_input.setEnabled(False)

        self.add_text_block_button = QPushButton("➕ Inserir Bloco de Texto na Seção")
        self.add_text_block_button.setEnabled(False)
        self.add_text_block_button.clicked.connect(self.add_text_block)

        self.ai_generate_text_button = QPushButton("🤖 IA: Gerar Texto Técnico")
        self.ai_generate_text_button.setEnabled(False)
        self.ai_generate_text_button.clicked.connect(self.ai_generate_section_text)

        self.section_tree.currentItemChanged.connect(self._section_selection_changed)
        self.section_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.section_tree.customContextMenuRequested.connect(self._show_section_context_menu)

        section_panel = QGroupBox("Manual Structure & Content Editor")
        section_layout = QVBoxLayout(section_panel)
        section_layout.addWidget(self.ai_suggest_button)
        section_layout.addWidget(self.section_name)
        section_layout.addWidget(self.add_section_button)
        section_layout.addWidget(self.rename_section_button)
        section_layout.addWidget(self.edit_content_button)
        section_layout.addWidget(self.subsection_name)
        section_layout.addWidget(self.add_subsection_button)
        section_layout.addWidget(self.section_tree)
        
        section_layout.addWidget(QLabel("Inserir Texto Personalizado (em qualquer parte):"))
        section_layout.addWidget(self.content_text_input)
        
        text_btn_layout = QHBoxLayout()
        text_btn_layout.addWidget(self.add_text_block_button)
        text_btn_layout.addWidget(self.ai_generate_text_button)
        section_layout.addLayout(text_btn_layout)
        section_layout.addWidget(self.remove_section_button)

        # Right panel: AI Chat Assistant & Translation settings
        right_panel_widget = QWidget()
        right_layout = QVBoxLayout(right_panel_widget)

        ai_chat_group = QGroupBox("🤖 Manus AI Assistant & Chat")
        ai_chat_layout = QVBoxLayout(ai_chat_group)
        
        # API Key, Base URL & Model input for free providers (Groq, etc.)
        api_key_layout = QHBoxLayout()
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("API Key (ex: gsk_...)")
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.textChanged.connect(self._on_api_key_changed)
        
        self.base_url_input = QLineEdit()
        self.base_url_input.setPlaceholderText("Base URL (ex: https://api.groq.com/openai/v1)")
        
        self.model_input = QLineEdit("llama-3.3-70b-versatile")
        self.model_input.setPlaceholderText("Model (ex: llama-3.3-70b-versatile)")
        
        save_key_button = QPushButton("Salvar Configs")
        save_key_button.clicked.connect(self._save_api_key)
        
        test_conn_button = QPushButton("Testar Conexão")
        test_conn_button.clicked.connect(self._test_ai_connection)
        
        api_key_layout.addWidget(self.api_key_input)
        api_key_layout.addWidget(self.base_url_input)
        api_key_layout.addWidget(self.model_input)
        api_key_layout.addWidget(save_key_button)
        api_key_layout.addWidget(test_conn_button)
        ai_chat_layout.addLayout(api_key_layout)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setPlainText("Bem-vindo! Faça perguntas à IA sobre o manual ou clique em 'Suggest Structure' para obter dicas de distribuição de páginas.\n(Dica: Funciona com assistente inteligente embutido ou com sua API Key inserida acima).")
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Ex: Qual seção é ideal para a página 5?")
        self.chat_input.returnPressed.connect(self.send_chat_message)
        self.chat_send_button = QPushButton("Enviar Pergunta à IA")
        self.chat_send_button.clicked.connect(self.send_chat_message)
        
        chat_input_layout = QHBoxLayout()
        chat_input_layout.addWidget(self.chat_input)
        chat_input_layout.addWidget(self.chat_send_button)

        self.image_review_button = QPushButton("🤖 Revisar Imagens Pendentes")
        self.image_review_button.setToolTip(
            "Lista, por seção e subseção, as imagens do HTML que precisam de captura ou recorte."
        )
        self.image_review_button.clicked.connect(
            lambda: self._show_pending_image_review(show_dialog=True)
        )

        ai_chat_layout.addWidget(self.chat_display)
        ai_chat_layout.addLayout(chat_input_layout)
        ai_chat_layout.addWidget(self.image_review_button)
        right_layout.addWidget(ai_chat_group)

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

        right_layout.addWidget(language_group)

        # Right panel now only contains AI Chat and Translation Settings
        # Preview gets its own central dedicated wide panel

        self.preview = QLabel("Abra um PDF, HTML ou imagens para começar")
        self.preview.setObjectName("preview")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(600, 750)
        
        preview_scroll = QScrollArea()
        preview_scroll.setWidgetResizable(True)
        preview_scroll.setWidget(self.preview)
        
        preview_group = QGroupBox("📄 Pré-visualização Ampliada do Manual")
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.addWidget(preview_scroll)

        # 4-Column / 4-Panel Master Splitter Layout for professional workflow
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(page_panel)        # 1. Pages list
        splitter.addWidget(preview_group)     # 2. Large central PDF preview
        splitter.addWidget(section_panel)     # 3. Sections & mixed content editor
        splitter.addWidget(right_panel_widget) # 4. AI Chat & Translation / Cover settings
        
        splitter.setSizes([200, 500, 350, 450])
        self.setCentralWidget(splitter)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.statusBar().addPermanentWidget(self.progress)
        self._restore_ai_settings()

    def _restore_ai_settings(self) -> None:
        """Restore local AI settings for this computer; project archives never contain secrets."""
        key = str(self._settings.value("ai/api_key", "") or "")
        base_url = str(self._settings.value("ai/base_url", "") or "")
        model = str(self._settings.value("ai/model", "") or "")
        self.api_key_input.setText(key)
        self.base_url_input.setText(base_url)
        if model:
            self.model_input.setText(model)
        if key or base_url or model:
            self._ai_service.update_key(key, base_url, self.model_input.text().strip())

    def _persist_ai_settings(self) -> None:
        """Persist AI credentials only in this user's local application settings."""
        self._settings.setValue("ai/api_key", self.api_key_input.text().strip())
        self._settings.setValue("ai/base_url", self.base_url_input.text().strip())
        self._settings.setValue("ai/model", self.model_input.text().strip())
        self._settings.sync()

    def _project_metadata(self) -> dict[str, object]:
        """Return editable UI data that belongs in a portable project archive."""
        return {
            "title": self.title_input.text().strip(),
            "code": self.code_input.text().strip(),
            "year": self.year_input.currentText(),
            "semester": self.semester_input.currentData(),
            "source_language": self.source_language.currentData(),
            "languages": {
                "pt": self.pt_language.isChecked(),
                "en": self.en_language.isChecked(),
                "es": self.es_language.isChecked(),
            },
        }

    def _apply_project_metadata(self, metadata: dict[str, object]) -> None:
        """Restore editable UI controls from an .e2ps manifest."""
        self.title_input.setText(str(metadata.get("title", "E2PS Technical Manual")))
        self.code_input.setText(str(metadata.get("code", "")))
        year = str(metadata.get("year", ""))
        if self.year_input.findText(year) >= 0:
            self.year_input.setCurrentText(year)
        semester = metadata.get("semester")
        semester_index = self.semester_input.findData(semester)
        if semester_index >= 0:
            self.semester_input.setCurrentIndex(semester_index)
        source_index = self.source_language.findData(metadata.get("source_language", "pt"))
        if source_index >= 0:
            self.source_language.setCurrentIndex(source_index)
        languages = metadata.get("languages", {})
        if isinstance(languages, dict):
            self.pt_language.setChecked(bool(languages.get("pt", True)))
            self.en_language.setChecked(bool(languages.get("en", False)))
            self.es_language.setChecked(bool(languages.get("es", False)))

    def _populate_page_list(self) -> None:
        """Render the current project pages in the source-page list."""
        self.page_list.clear()
        for page in self._pages:
            item = QListWidgetItem(page.display_name)
            item.setData(Qt.ItemDataRole.UserRole, page)
            item.setCheckState(Qt.CheckState.Unchecked)
            item.setIcon(QIcon(str(page.thumbnail_path)))
            item.setSizeHint(QSize(0, 42))
            self.page_list.addItem(item)

    def save_e2ps_project(self) -> None:
        """Save all manual assets and editable structure to a portable .e2ps project file."""
        if not self._pages:
            QMessageBox.warning(self, "Projeto vazio", "Abra páginas ou imagens antes de salvar o projeto.")
            return
        suggested_name = self._project_path or Path(self.title_input.text().strip() or "manual_e2ps").with_suffix(".e2ps")
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar Projeto E2PS Manual Builder",
            str(suggested_name),
            "E2PS Manual Builder Project (*.e2ps)",
        )
        if not filename:
            return
        try:
            saved_path = self._project_files.save_project(
                Path(filename),
                self._pages,
                self._sections,
                self._project_metadata(),
                self._cover_image_path,
            )
        except Exception as error:
            QMessageBox.critical(self, "Erro ao salvar projeto", str(error))
            return
        self._project_path = saved_path
        self.statusBar().showMessage(f"Projeto salvo em {saved_path.name}", 6000)
        QMessageBox.information(
            self,
            "Projeto salvo",
            "O arquivo .e2ps foi salvo com as páginas, recortes, capa, seções, subseções e blocos de texto.\n\n"
            "Por segurança, a chave da IA não é incluída no arquivo .e2ps; ela permanece apenas neste computador.",
        )

    def open_e2ps_project(self) -> None:
        """Open a portable .e2ps project and restore it to this app session."""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Abrir Projeto E2PS Manual Builder",
            "",
            "E2PS Manual Builder Project (*.e2ps *.emb)",
        )
        if not filename:
            return
        restore_root = Path(self._temp_dir.name) / "restored_e2ps_project"
        if restore_root.exists():
            import shutil
            shutil.rmtree(restore_root)
        try:
            loaded = self._project_files.load_project(Path(filename), restore_root)
        except Exception as error:
            QMessageBox.critical(self, "Erro ao abrir projeto", str(error))
            return
        self._pages = loaded.pages
        self._sections = loaded.sections
        self._cover_image_path = loaded.cover_image_path
        self.cover_path_input.setText(str(loaded.cover_image_path) if loaded.cover_image_path else "")
        self._project_path = Path(filename)
        self._apply_project_metadata(loaded.metadata)
        self._populate_page_list()
        self._refresh_sections()
        has_pages = bool(self._pages)
        self.select_all_button.setEnabled(has_pages)
        self.clear_selection_button.setEnabled(has_pages)
        self.crop_page_button.setEnabled(has_pages)
        self.ai_suggest_button.setEnabled(has_pages)
        self.add_section_button.setEnabled(has_pages)
        self.export_button.setEnabled(bool(self._sections))
        self.save_project_action.setEnabled(has_pages)
        self.progress.setVisible(False)
        self.statusBar().showMessage(
            f"Projeto aberto: {Path(filename).name} ({len(self._pages)} páginas, {len(self._sections)} seções)",
            7000,
        )

    def open_pdf(self) -> None:
        """Open a PDF file and start background rendering."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open PDF Manual", "", "PDF Documents (*.pdf)"
        )
        if not file_path:
            return
        self._pages.clear()
        self._sections.clear()
        self._project_path = None
        self.page_list.clear()
        self.section_tree.clear()
        self.export_button.setEnabled(False)
        self.save_project_action.setEnabled(False)
        self.select_all_button.setEnabled(False)
        self.clear_selection_button.setEnabled(False)
        self.crop_page_button.setEnabled(False)
        self.ai_suggest_button.setEnabled(False)
        self.add_section_button.setEnabled(False)

        self._render_worker = PdfRenderWorker(Path(file_path), Path(self._temp_dir.name))
        self._render_worker.progress_changed.connect(self._update_render_progress)
        self._render_worker.completed.connect(self._rendering_completed)
        self._render_worker.failed.connect(self._rendering_failed)

        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setVisible(True)
        self._render_worker.start()
        self.statusBar().showMessage("Rendering PDF pages...")

    def open_html(self) -> None:
        """Open a static HTML/HTM manual and render it as editable visual pages."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Abrir Manual HTML",
            "",
            "Arquivos HTML (*.html *.htm)",
        )
        if not file_path:
            return

        self._pages.clear()
        self._sections.clear()
        self._project_path = None
        self.page_list.clear()
        self.section_tree.clear()
        self.export_button.setEnabled(False)
        self.save_project_action.setEnabled(False)
        self.select_all_button.setEnabled(False)
        self.clear_selection_button.setEnabled(False)
        self.crop_page_button.setEnabled(False)
        self.ai_suggest_button.setEnabled(False)
        self.add_section_button.setEnabled(False)

        destination = Path(self._temp_dir.name) / "html_render"
        if destination.exists():
            import shutil
            shutil.rmtree(destination)
        self._html_render_worker = HtmlRenderWorker(Path(file_path), destination)
        self._html_render_worker.progress_changed.connect(self._update_render_progress)
        self._html_render_worker.completed.connect(self._html_rendering_completed)
        self._html_render_worker.failed.connect(self._rendering_failed)

        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setVisible(True)
        self._html_render_worker.start()
        self.statusBar().showMessage("Lendo o HTML, extraindo texto-fonte e criando pré-visualizações…")

    def open_images(self) -> None:
        """Open multiple image files directly as manual pages without PDF conversion."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Selecionar Imagens do Manual",
            "",
            "Imagens (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if not file_paths:
            return
        
        self._pages.clear()
        self._sections.clear()
        self._project_path = None
        self.page_list.clear()
        self.section_tree.clear()
        self.export_button.setEnabled(False)
        self.save_project_action.setEnabled(False)
        self.select_all_button.setEnabled(False)
        self.clear_selection_button.setEnabled(False)
        self.crop_page_button.setEnabled(False)
        self.ai_suggest_button.setEnabled(False)
        self.add_section_button.setEnabled(False)
        
        pages = []
        temp_dir = Path(self._temp_dir.name)
        for i, path_str in enumerate(file_paths, start=1):
            src_path = Path(path_str)
            variant = 1
            dest_image_path = temp_dir / f"page_{i:03d}_{variant:02d}.png"
            dest_thumb_path = temp_dir / f"thumbnail_{i:03d}_{variant:02d}.png"
            
            try:
                if Image is None:
                    raise ImportError("Pillow (PIL) não está instalado no ambiente Python.")
                img = Image.open(src_path)
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.save(dest_image_path, "PNG")
                
                thumb = img.copy()
                thumb.thumbnail((150, 150))
                thumb.save(dest_thumb_path, "PNG")
                
                pdf_page = PdfPage(
                    number=i,
                    image_path=dest_image_path,
                    thumbnail_path=dest_thumb_path,
                    variant=variant,
                    extracted_text=f"Imagem direta {src_path.stem}",
                    source_type="image",
                )
                pages.append(pdf_page)
            except Exception as e:
                QMessageBox.warning(self, "Erro ao carregar imagem", f"Não foi possível processar {src_path.name}:\n{e}")
                
        if pages:
            self._rendering_completed(pages)
            self.statusBar().showMessage(f"Carregadas {len(pages)} imagens diretamente com sucesso.")

    def _update_render_progress(self, current: int, total: int) -> None:
        if total > 0:
            self.progress.setValue(int((current / total) * 100))

    def _rendering_completed(self, pages: list[PdfPage]) -> None:
        self._pages = pages
        self._populate_page_list()

        self.progress.setVisible(False)
        self.select_all_button.setEnabled(True)
        self.clear_selection_button.setEnabled(True)
        self.crop_page_button.setEnabled(True)
        self.ai_suggest_button.setEnabled(bool(self._pages))
        self.add_section_button.setEnabled(bool(self._pages))
        self.save_project_action.setEnabled(bool(self._pages))
        html_pages = sum(1 for page in pages if page.source_type == "html")
        if html_pages:
            self.statusBar().showMessage(
                f"HTML importado com {len(pages)} página(s) visuais e texto-fonte extraído para a IA."
            )
        else:
            self.statusBar().showMessage(f"Carregadas {len(pages)} página(s) do manual.")

        if any(page.source_type == "pdf" and page.variant == 1 for page in pages):
            self._start_pdf_structure_analysis()

    def _start_pdf_structure_analysis(self) -> None:
        """Analyze a manufacturer PDF after rendering and create a compact E2PS outline."""
        pdf_pages = [
            page for page in self._pages
            if page.source_type == "pdf" and page.variant == 1
        ]
        if not pdf_pages:
            return
        self._pdf_structure_worker = PdfStructureWorker(
            pdf_pages,
            self.title_input.text().strip(),
            self.api_key_input.text().strip(),
            self.base_url_input.text().strip(),
            self.model_input.text().strip() or "llama-3.3-70b-versatile",
        )
        self._pdf_structure_worker.completed.connect(self._pdf_structure_completed)
        self._pdf_structure_worker.failed.connect(self._pdf_structure_failed)
        self._pdf_structure_worker.start()
        self.statusBar().showMessage(
            "A IA está selecionando somente o conteúdo essencial do PDF para o manual E2PS…"
        )

    def _pdf_structure_completed(self, plan: PdfStructurePlan) -> None:
        """Convert the selected PDF outline into the same editable section models used by HTML."""
        if not plan.sections:
            message = plan.note or "Não foi possível identificar conteúdo técnico suficiente no PDF."
            self.chat_display.append(
                "<br><b>🤖 Análise automática do PDF:</b><br>" + escape(message)
            )
            self.statusBar().showMessage(message, 9000)
            return

        created_sections = self._build_sections_from_pdf_plan(plan)
        default_title = "E2PS Technical Manual"
        if plan.document_title.strip() and (
            not self.title_input.text().strip()
            or self.title_input.text().strip() == default_title
        ):
            self.title_input.setText(plan.document_title.strip())
        self._refresh_sections()
        self.export_button.setEnabled(bool(self._sections))

        selected_count = len(plan.selected_page_numbers)
        omitted_count = len(plan.omitted_page_numbers)
        mode = "IA" if plan.used_ai else "análise local"
        summary = (
            f"Foram criadas {created_sections} seção(ões) editáveis com {selected_count} página(s) "
            f"técnicas selecionadas pela {mode}. {omitted_count} página(s) de capa, referência, "
            "marketing, duplicidade ou conteúdo não operacional foram deixadas de fora."
        )
        if plan.note:
            summary += " " + plan.note
        self.chat_display.append(
            "<br><b>🤖 Estrutura enxuta do PDF criada:</b><br>" + escape(summary)
        )
        self.statusBar().showMessage(summary, 12000)

    def _pdf_structure_failed(self, error: str) -> None:
        """Keep rendered pages available when background PDF analysis cannot run."""
        message = (
            "As páginas foram carregadas, mas a estrutura automática do PDF não pôde ser criada: "
            f"{error}"
        )
        self.chat_display.append(
            "<br><b>🤖 Análise automática do PDF:</b><br>" + escape(message)
        )
        self.statusBar().showMessage(message, 10000)

    def _build_sections_from_pdf_plan(self, plan: PdfStructurePlan) -> int:
        """Map an AI-selected PDF plan to editable mixed content blocks.

        Pages are initially set to text/table mode so the export can reconstruct readable
        technical content. The user may replace them with images or recrops in the editor.
        """
        from dataclasses import replace

        available_pages = {
            page.number: page
            for page in self._pages
            if page.source_type == "pdf" and page.variant == 1
        }

        def selected_content(intro: str, page_numbers: list[int]) -> list[PdfPage | str]:
            content: list[PdfPage | str] = []
            if intro.strip():
                content.append(intro.strip())
            for page_number in page_numbers:
                page = available_pages.get(page_number)
                if page is not None:
                    content.append(replace(page, export_mode="text"))
            return content

        self._sections.clear()
        for outline_section in plan.sections:
            subsections = [
                ManualSubsection(
                    title=outline_subsection.title,
                    content=selected_content(
                        outline_subsection.intro,
                        outline_subsection.page_numbers,
                    ),
                )
                for outline_subsection in outline_section.subsections
            ]
            self._sections.append(
                ManualSection(
                    title=outline_section.title,
                    content=selected_content(
                        outline_section.intro,
                        outline_section.page_numbers,
                    ),
                    subsections=subsections,
                )
            )
        return len(self._sections)

    def _html_rendering_completed(
        self,
        pages: list[PdfPage],
        plan: HtmlStructurePlan,
    ) -> None:
        """Finalize an HTML import and turn its semantic outline into editable content."""
        self._rendering_completed(pages)
        created_sections = self._build_sections_from_html_plan(plan)

        if plan.document_title.strip():
            self.title_input.setText(plan.document_title.strip())

        self._refresh_sections()
        self.export_button.setEnabled(bool(self._sections))

        summary = f"Foram criadas {created_sections} seção(ões) editáveis a partir da estrutura do HTML."
        if plan.image_count:
            summary += (
                f" Foram identificadas {plan.image_count} imagem(ns) que precisam ser revisadas "
                "na pré-visualização e, se necessárias no manual, incluídas como recortes ou capturas."
            )
        else:
            summary += " Nenhuma imagem que exija captura foi identificada na estrutura semântica."
        self.chat_display.append(
            "<br><b>🤖 Estrutura HTML criada automaticamente:</b><br>"
            f"{escape(summary)}"
        )
        self.statusBar().showMessage(summary, 9000)
        if plan.image_count:
            self._show_pending_image_review()

    def _build_sections_from_html_plan(self, plan: HtmlStructurePlan) -> int:
        """Map the semantic HTML plan to the regular, fully editable manual models."""
        self._sections.clear()
        for outline_section in plan.sections:
            section_content = list(outline_section.content)
            section_content.extend(hint.message for hint in outline_section.image_hints)
            subsections = []
            for outline_subsection in outline_section.subsections:
                subsection_content = list(outline_subsection.content)
                subsection_content.extend(
                    hint.message for hint in outline_subsection.image_hints
                )
                subsections.append(
                    ManualSubsection(
                        title=outline_subsection.title,
                        content=subsection_content,
                    )
                )
            self._sections.append(
                ManualSection(
                    title=outline_section.title,
                    content=section_content,
                    subsections=subsections,
                )
            )
        return len(self._sections)

    def _pending_image_locations(self) -> list[str]:
        """Return only the section/subsection locations that contain image-capture notices."""
        pending: list[str] = []
        for section in self._sections:
            section_location = f"Seção \"{section.title}\""
            if any(
                isinstance(content, str) and content.startswith("Imagem encontrada:")
                for content in section.content
            ):
                pending.append(section_location)
            for subsection in section.subsections:
                if any(
                    isinstance(content, str) and content.startswith("Imagem encontrada:")
                    for content in subsection.content
                ):
                    pending.append(f"{section_location} › Subseção \"{subsection.title}\"")
        return list(dict.fromkeys(pending))

    def _show_pending_image_review(self, show_dialog: bool = False) -> None:
        """Display image-capture locations in the AI panel and, when requested, a dialog."""
        pending = self._pending_image_locations()
        if not pending:
            message = (
                "Nenhuma imagem pendente de captura foi encontrada nas seções atuais.\n\n"
                "Se você ainda precisar incluir uma figura, crie um recorte da pré-visualização "
                "ou importe uma imagem e adicione-a à seção desejada."
            )
            self.chat_display.append(
                "<br><b>🤖 Revisão de imagens pendentes:</b><br>"
                f"{escape(message).replace(chr(10), '<br>')}"
            )
            self.statusBar().showMessage("Nenhuma imagem pendente de captura.", 5000)
        else:
            location_lines = "\n".join(f"• {location}" for location in pending)
            message = (
                "Há imagens pendentes nas seguintes partes do manual:\n\n"
                f"{location_lines}\n\n"
                "Abra a pré-visualização, crie um recorte ou importe uma imagem. Em seguida, "
                "use Editar conteúdo na seção indicada para posicioná-la no manual."
            )
            items = "".join(f"<li>{escape(location)}</li>" for location in pending)
            self.chat_display.append(
                "<br><b>🤖 Revisão de imagens pendentes:</b><br>"
                "Há imagens pendentes nas partes abaixo. Abra a pré-visualização, crie um recorte "
                "ou importe uma imagem e, depois, use Editar conteúdo para adicioná-la à parte indicada."
                f"<ol>{items}</ol>"
            )
            self.statusBar().showMessage(
                f"Há imagens pendentes em {len(pending)} seção(ões). Veja a revisão.",
                9000,
            )

        if show_dialog:
            QMessageBox.information(self, "Revisar imagens pendentes", message)

    def _rendering_failed(self, error: str) -> None:
        self.progress.setVisible(False)
        self.preview.setText("Não foi possível renderizar este arquivo")
        QMessageBox.critical(
            self,
            "Erro ao abrir manual",
            f"O arquivo não pôde ser convertido em páginas.\n\n{error}",
        )
        self.statusBar().showMessage("Falha ao renderizar o manual")

    def _show_current_page(self, item: QListWidgetItem | None) -> None:
        if item is None:
            self.export_mode_combo.setEnabled(False)
            return
        page = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(page, PdfPage):
            self.export_mode_combo.setEnabled(False)
            return
        
        # Atualizar combo de modo de exportação para a página selecionada
        self.export_mode_combo.setEnabled(True)
        mode_idx = self.export_mode_combo.findData(getattr(page, "export_mode", "image"))
        self.export_mode_combo.setCurrentIndex(mode_idx)

        pixmap = QPixmap(str(page.image_path))
        # Exibir com resolução otimizada (500px de largura) para caber 100% dentro da aba de visualização
        scaled_pixmap = pixmap.scaledToWidth(500, Qt.TransformationMode.SmoothTransformation)
        self.preview.setPixmap(scaled_pixmap)
        self.preview.resize(scaled_pixmap.size())

    def _change_page_export_mode(self, index: int) -> None:
        """Update the export mode (image/text) for the currently selected page."""
        item = self.page_list.currentItem()
        if item is None:
            return
        page = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(page, PdfPage):
            return
        
        new_mode = self.export_mode_combo.itemData(index)
        # Como PdfPage é frozen, precisamos criar uma nova instância com o modo atualizado
        from dataclasses import replace
        new_page = replace(page, export_mode=new_mode)
        
        # Atualizar na lista interna _pages
        for i, p in enumerate(self._pages):
            if p.number == page.number and p.variant == page.variant:
                self._pages[i] = new_page
                break
        
        # Atualizar as referências já inseridas nas seções, inclusive as criadas automaticamente.
        for section in self._sections:
            section.content = [
                new_page if isinstance(content, PdfPage) and content.number == page.number
                and content.variant == page.variant else content
                for content in section.content
            ]
            for subsection in section.subsections:
                subsection.content = [
                    new_page if isinstance(content, PdfPage) and content.number == page.number
                    and content.variant == page.variant else content
                    for content in subsection.content
                ]

        # Atualizar o item da lista
        item.setData(Qt.ItemDataRole.UserRole, new_page)
        self.statusBar().showMessage(f"Página {page.number} configurada para exportação como {new_mode}.")

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
        key = self.api_key_input.text().strip()
        endpoint = self.base_url_input.text().strip()
        model_name = self.model_input.text().strip() or "llama-3.3-70b-versatile"
        self._export_worker = MultilingualExportWorker(
            Path(destination),
            self.title_input.text().strip(),
            self._sections,
            self.code_input.text().strip(),
            self._publication_date(),
            languages,
            source_language,
            "groq" if endpoint or key else "manus",
            key,
            endpoint,
            model=model_name,
            cover_image_path=cover_path,
        )
        self._export_worker.progress_changed.connect(self._update_export_progress)
        self._export_worker.completed.connect(self._export_finished)
        self._export_worker.failed.connect(self._export_failed)
        # Progresso percentual: evita a impressão de carregamento infinito.
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setVisible(True)
        self.export_button.setEnabled(False)
        self._export_worker.start()
        self.statusBar().showMessage("Exportando projeto e analisando páginas com IA…")

    def add_section(self) -> None:
        """Create a named section from currently checked page items."""
        title = self.section_name.text().strip()
        pages = self._checked_pages()
        if not title:
            QMessageBox.warning(self, "Section name required", "Enter a title for the section.")
            return
        # Initialize section with pages as content blocks
        section = ManualSection(title=title, content=list(pages))
        self._sections.append(section)
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
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        item_type, section_index, subsection_index = data
        if item_type == "section":
            self._sections.pop(section_index)
        else:
            self._sections[section_index].subsections.pop(subsection_index)
        self._refresh_sections()
        self.export_button.setEnabled(bool(self._sections))
        self.content_text_input.clear()
        self.content_text_input.setEnabled(False)
        self.add_text_block_button.setEnabled(False)
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
        crop_page = PdfPage(
            page.number,
            image_path,
            thumbnail_path,
            next_variant,
            page.extracted_text,
            page.export_mode,
            page.source_type,
        )
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
            item_count = len(section.content)
            parent = QTreeWidgetItem([f"{index}. {section.title} ({item_count} itens)"])
            parent.setData(0, Qt.ItemDataRole.UserRole, ("section", index - 1, -1))
            self.section_tree.addTopLevelItem(parent)
            for sub_index, subsection in enumerate(section.subsections, start=1):
                sub_count = len(subsection.content)
                child = QTreeWidgetItem([f"{sub_index}. {subsection.title} ({sub_count} itens)"])
                child.setData(
                    0,
                    Qt.ItemDataRole.UserRole,
                    ("subsection", index - 1, sub_index - 1),
                )
                parent.addChild(child)
            parent.setExpanded(True)

    def _show_section_context_menu(self, position) -> None:
        """Show editing, deletion and ordering actions for the clicked tree item."""
        item = self.section_tree.itemAt(position)
        if item is None:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        item_type, section_index, subsection_index = data
        self.section_tree.setCurrentItem(item)

        menu = QMenu(self)
        edit_content_action = menu.addAction("Editar conteúdo…")
        rename_action = menu.addAction("Renomear título…")
        delete_action = menu.addAction("Excluir seção" if item_type == "section" else "Excluir subseção")
        menu.addSeparator()
        move_up_action = menu.addAction(
            "Mover seção para cima" if item_type == "section" else "Mover subseção para cima"
        )
        move_down_action = menu.addAction(
            "Mover seção para baixo" if item_type == "section" else "Mover subseção para baixo"
        )

        if item_type == "section":
            move_up_action.setEnabled(section_index > 0)
            move_down_action.setEnabled(section_index < len(self._sections) - 1)
        else:
            siblings = self._sections[section_index].subsections
            move_up_action.setEnabled(subsection_index > 0)
            move_down_action.setEnabled(subsection_index < len(siblings) - 1)

        selected_action = menu.exec(self.section_tree.viewport().mapToGlobal(position))
        if selected_action == edit_content_action:
            self.edit_selected_content()
        elif selected_action == rename_action:
            self.rename_selected_item()
        elif selected_action == delete_action:
            self.remove_selected_section()
        elif selected_action == move_up_action:
            self._move_selected_item(-1)
        elif selected_action == move_down_action:
            self._move_selected_item(1)

    def _move_selected_item(self, direction: int) -> None:
        """Move the selected section or subsection one position in its own hierarchy."""
        item = self.section_tree.currentItem()
        if item is None or direction not in {-1, 1}:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        item_type, section_index, subsection_index = data

        if item_type == "section":
            destination_index = section_index + direction
            if not 0 <= destination_index < len(self._sections):
                return
            self._sections[section_index], self._sections[destination_index] = (
                self._sections[destination_index],
                self._sections[section_index],
            )
            self._refresh_sections()
            self.section_tree.setCurrentItem(
                self.section_tree.topLevelItem(destination_index)
            )
            self.statusBar().showMessage("Ordem da seção atualizada.", 4000)
            return

        siblings = self._sections[section_index].subsections
        destination_index = subsection_index + direction
        if not 0 <= destination_index < len(siblings):
            return
        siblings[subsection_index], siblings[destination_index] = (
            siblings[destination_index],
            siblings[subsection_index],
        )
        self._refresh_sections()
        parent = self.section_tree.topLevelItem(section_index)
        self.section_tree.setCurrentItem(parent.child(destination_index))
        self.statusBar().showMessage("Ordem da subseção atualizada.", 4000)

    def _section_selection_changed(
        self,
        current: QTreeWidgetItem | None,
        previous: QTreeWidgetItem | None,
    ) -> None:
        """Enable section actions when an item is selected."""
        has_selection = current is not None
        self.remove_section_button.setEnabled(has_selection)
        self.rename_section_button.setEnabled(has_selection)
        self.edit_content_button.setEnabled(has_selection)
        self.add_subsection_button.setEnabled(has_selection)
        self.content_text_input.setEnabled(has_selection)
        self.add_text_block_button.setEnabled(has_selection)
        self.ai_generate_text_button.setEnabled(has_selection)

    def edit_selected_content(self) -> None:
        """Open the mixed-content editor for the selected section or subsection."""
        item = self.section_tree.currentItem()
        if item is None:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        item_type, section_index, subsection_index = data
        target_obj = (
            self._sections[section_index]
            if item_type == "section"
            else self._sections[section_index].subsections[subsection_index]
        )
        dialog = ContentEditorDialog(
            target_obj.title,
            target_obj.content,
            self._pages,
            self,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        target_obj.content = dialog.content
        self._refresh_sections()
        if item_type == "section":
            self.section_tree.setCurrentItem(self.section_tree.topLevelItem(section_index))
        else:
            parent = self.section_tree.topLevelItem(section_index)
            self.section_tree.setCurrentItem(parent.child(subsection_index))
        self.statusBar().showMessage("Conteúdo da seção atualizado.", 5000)

    def rename_selected_item(self) -> None:
        """Rename selected section or subsection using dialog."""
        item = self.section_tree.currentItem()
        if item is None:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        item_type, section_index, subsection_index = data
        target_obj = (
            self._sections[section_index]
            if item_type == "section"
            else self._sections[section_index].subsections[subsection_index]
        )
        from PySide6.QtWidgets import QInputDialog
        new_title, ok = QInputDialog.getText(
            self, "Editar Título", "Novo título:", text=target_obj.title
        )
        if ok and new_title.strip():
            target_obj.title = new_title.strip()
            self._refresh_sections()
            self.statusBar().showMessage(f"Título atualizado para '{new_title.strip()}'")

    def add_subsection(self) -> None:
        """Create a subsection under the selected section from checked pages."""
        title = self.subsection_name.text().strip()
        pages = self._checked_pages()
        item = self.section_tree.currentItem()
        if not title or item is None:
            QMessageBox.warning(
                self,
                "Subsection details required",
                "Select a section and enter a subsection name.",
            )
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        _, section_index, _ = data
        self._sections[section_index].subsections.append(
            ManualSubsection(title=title, content=list(pages))
        )
        self.subsection_name.clear()
        self.deselect_all_pages()
        self._refresh_sections()

    def add_text_block(self) -> None:
        """Insert a text block into the currently selected section or subsection."""
        item = self.section_tree.currentItem()
        if item is None:
            return
        text = self.content_text_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Texto vazio", "Escreva algum texto antes de adicionar.")
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        item_type, section_index, subsection_index = data
        if item_type == "section":
            self._sections[section_index].content.append(text)
        else:
            self._sections[section_index].subsections[subsection_index].content.append(text)
        self.content_text_input.clear()
        self._refresh_sections()
        self.statusBar().showMessage("Bloco de texto inserido na seção com sucesso.")

    def ai_suggest_structure(self) -> None:
        """Ask Manus AI to analyze pages and provide structural suggestions in the chat panel."""
        if not self._pages:
            QMessageBox.warning(self, "No pages", "Open a PDF first.")
            return
        suggestion = self._ai_service.suggest_structure_text(self._pages, self.title_input.text())
        self.chat_display.append(f"\n<b>🤖 [Sugestão de Estrutura da IA]:</b><br>{suggestion}<br>")
        self.statusBar().showMessage("IA gerou sugestão de estrutura no painel de chat.")

    def _test_ai_connection(self) -> None:
        """Test API connection with current settings."""
        success, message = self._ai_service.test_connection()
        if success:
            QMessageBox.information(self, "Sucesso", message)
        else:
            QMessageBox.warning(self, "Falha na Conexão", message)

    def ai_generate_section_text(self) -> None:
        """Generate professional technical text using AI and insert it as a content block."""
        item = self.section_tree.currentItem()
        if item is None:
            QMessageBox.warning(self, "Selecione uma seção", "Selecione uma seção ou subseção na árvore primeiro.")
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        item_type, section_index, subsection_index = data
        sec_title = self._sections[section_index].title if item_type == "section" else self._sections[section_index].subsections[subsection_index].title
        
        self.statusBar().showMessage("Gerando texto técnico com Manus AI...")
        generated = self._ai_service.generate_section_text(sec_title, self.title_input.text())
        self.content_text_input.setPlainText(generated)
        self.statusBar().showMessage("Texto técnico gerado com sucesso!")

    def send_chat_message(self) -> None:
        """Send user message to AI chat assistant with real PDF text context."""
        msg = self.chat_input.text().strip()
        if not msg:
            return
        self.chat_display.append(f"<br><b>Você:</b> {msg}")
        self.chat_input.clear()
        
        if self._pages:
            snippets = []
            for p in self._pages:
                snippet = p.extracted_text[:250].replace("\n", " ")
                snippets.append(f"Página {p.number}: {snippet}")
            pdf_context = "\n".join(snippets)
        else:
            pdf_context = "Nenhum PDF aberto no momento."
            
        reply = self._ai_service.ask_ai(msg, pdf_context)
        self.chat_display.append(f"<br><b>🤖 Manus AI:</b> {reply}")

    def _on_api_key_changed(self, text: str) -> None:
        """Auto-fill Groq default URL and model if a Groq key (gsk_) is pasted."""
        if text.strip().startswith("gsk_"):
            if not self.base_url_input.text().strip():
                self.base_url_input.setText("https://api.groq.com/openai/v1")
            if not self.model_input.text().strip():
                self.model_input.setText("llama-3.3-70b-versatile")

    def _save_api_key(self) -> None:
        """Save user provided API key, base URL and model into AI service."""
        key = self.api_key_input.text().strip()
        base_url = self.base_url_input.text().strip()
        model = self.model_input.text().strip()
        self._ai_service.update_key(key, base_url, model)
        self._persist_ai_settings()
        QMessageBox.information(self, "Configurações Salvas", f"Configurações salvas neste computador!\nModelo: {model or 'llama-3.3-70b-versatile'}\nBase URL: {base_url or 'OpenAI Default'}")
        self.statusBar().showMessage("Configurações de IA atualizadas.")

    def closeEvent(self, event) -> None:
        """Keep the current AI configuration available on this computer after restart."""
        self._persist_ai_settings()
        super().closeEvent(event)

    def _browse_cover_image(self) -> None:
        """Open file dialog to select manual cover image."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Cover Image", "", "Image Files (*.png *.jpg *.jpeg)"
        )
        if file_path:
            self._cover_image_path = Path(file_path)
            self.cover_path_input.setText(file_path)

    def _selected_languages(self) -> list[str]:
        """Return list of selected language codes."""
        codes = []
        if self.pt_language.isChecked():
            codes.append("pt")
        if self.en_language.isChecked():
            codes.append("en")
        if self.es_language.isChecked():
            codes.append("es")
        return codes

    def _publication_date(self) -> str:
        """Return publication date string in YYYY-MM format."""
        year = self.year_input.currentText()
        semester = self.semester_input.currentData()
        return f"{year}-{semester}"

    def _update_export_progress(self, current: int, total: int) -> None:
        """Update progress bar during background export."""
        if total > 0:
            percent = int((current / total) * 100)
            self.progress.setRange(0, 100)
            self.progress.setValue(percent)
            self.statusBar().showMessage(
                f"Exportando páginas: {current} de {total} ({percent}%)…"
            )

    def _export_finished(self, project_dir: Path) -> None:
        """Handle successful export completion."""
        self.progress.setVisible(False)
        self.export_button.setEnabled(True)
        QMessageBox.information(
            self,
            "Export Successful",
            f"The manual project has been successfully created at:\n\n{project_dir}",
        )
        self.statusBar().showMessage(f"Project saved at {project_dir}")

    def _export_failed(self, error: str) -> None:
        """Handle export failure."""
        self.progress.setVisible(False)
        self.export_button.setEnabled(True)
        QMessageBox.critical(self, "Export Error", f"The project could not be exported.\n\n{error}")
        self.statusBar().showMessage("Export failed")
