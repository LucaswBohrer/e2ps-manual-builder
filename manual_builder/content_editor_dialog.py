"""Interactive editor for the mixed text and page content of a manual section."""

from __future__ import annotations

from typing import Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from manual_builder.models import PdfPage


class ContentEditorDialog(QDialog):
    """Edit the ordered mixture of text blocks and imported pages in one target."""

    def __init__(
        self,
        title: str,
        content: Sequence[PdfPage | str],
        available_pages: Sequence[PdfPage],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Editar conteúdo — {title}")
        self.resize(820, 580)
        self._content: list[PdfPage | str] = list(content)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Edite a ordem e o conteúdo abaixo. Textos e avisos de imagem podem ser alterados; "
                "páginas e recortes podem ser incluídos na posição selecionada."
            )
        )

        content_layout = QHBoxLayout()
        self.content_list = QListWidget()
        self.content_list.setMinimumWidth(360)
        self.content_list.currentRowChanged.connect(self._load_selected_text)
        content_layout.addWidget(self.content_list, stretch=1)

        editor_layout = QVBoxLayout()
        editor_layout.addWidget(QLabel("Texto do item selecionado:"))
        self.text_editor = QTextEdit()
        self.text_editor.setPlaceholderText(
            "Selecione um texto ou aviso de imagem para alterá-lo, ou escreva um novo bloco."
        )
        editor_layout.addWidget(self.text_editor, stretch=1)
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        editor_layout.addWidget(self.status_label)
        content_layout.addLayout(editor_layout, stretch=1)
        layout.addLayout(content_layout, stretch=1)

        text_actions = QHBoxLayout()
        self.save_text_button = QPushButton("Salvar texto selecionado")
        self.save_text_button.clicked.connect(self._save_selected_text)
        self.add_text_button = QPushButton("Adicionar texto após o selecionado")
        self.add_text_button.clicked.connect(self._add_text)
        text_actions.addWidget(self.save_text_button)
        text_actions.addWidget(self.add_text_button)
        layout.addLayout(text_actions)

        page_layout = QGridLayout()
        page_layout.addWidget(QLabel("Adicionar página/recorte:"), 0, 0)
        self.page_picker = QComboBox()
        for page in available_pages:
            self.page_picker.addItem(page.display_name, page)
        page_layout.addWidget(self.page_picker, 0, 1)
        self.add_page_button = QPushButton("Inserir página após o selecionado")
        self.add_page_button.clicked.connect(self._add_page)
        self.add_page_button.setEnabled(bool(available_pages))
        page_layout.addWidget(self.add_page_button, 0, 2)
        layout.addLayout(page_layout)

        order_actions = QHBoxLayout()
        self.move_up_button = QPushButton("Mover item para cima")
        self.move_up_button.clicked.connect(lambda: self._move_selected_item(-1))
        self.move_down_button = QPushButton("Mover item para baixo")
        self.move_down_button.clicked.connect(lambda: self._move_selected_item(1))
        self.remove_button = QPushButton("Remover item selecionado")
        self.remove_button.clicked.connect(self._remove_selected_item)
        order_actions.addWidget(self.move_up_button)
        order_actions.addWidget(self.move_down_button)
        order_actions.addWidget(self.remove_button)
        layout.addLayout(order_actions)

        dialog_buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        dialog_buttons.accepted.connect(self.accept)
        dialog_buttons.rejected.connect(self.reject)
        layout.addWidget(dialog_buttons)

        self._refresh_items()

    @property
    def content(self) -> list[PdfPage | str]:
        """Return the edited content in its current order."""
        return list(self._content)

    def _display_name(self, item: PdfPage | str) -> str:
        if isinstance(item, PdfPage):
            return f"📄 {item.display_name}"
        compact_text = " ".join(item.strip().split())
        if not compact_text:
            return "✍️ Bloco de texto vazio"
        if len(compact_text) > 105:
            compact_text = f"{compact_text[:102]}…"
        return f"✍️ {compact_text}"

    def _refresh_items(self, selected_row: int | None = None) -> None:
        if selected_row is None:
            selected_row = self.content_list.currentRow()
        self.content_list.blockSignals(True)
        self.content_list.clear()
        for index, item in enumerate(self._content, start=1):
            list_item = QListWidgetItem(f"{index}. {self._display_name(item)}")
            self.content_list.addItem(list_item)
        self.content_list.blockSignals(False)

        if self._content:
            row = max(0, min(selected_row, len(self._content) - 1))
            self.content_list.setCurrentRow(row)
        else:
            self.text_editor.clear()
            self.text_editor.setEnabled(False)
            self.save_text_button.setEnabled(False)
            self.move_up_button.setEnabled(False)
            self.move_down_button.setEnabled(False)
            self.remove_button.setEnabled(False)

    def _load_selected_text(self, row: int) -> None:
        if not 0 <= row < len(self._content):
            return
        item = self._content[row]
        is_text = isinstance(item, str)
        self.text_editor.setEnabled(is_text)
        self.save_text_button.setEnabled(is_text)
        if is_text:
            self.text_editor.setPlainText(item)
            self.status_label.setText("Você pode alterar este texto e salvar a mudança.")
        else:
            self.text_editor.clear()
            self.status_label.setText(
                "Este é um item de página/recorte. Use os botões abaixo para mover ou remover."
            )
        self.move_up_button.setEnabled(row > 0)
        self.move_down_button.setEnabled(row < len(self._content) - 1)
        self.remove_button.setEnabled(True)

    def _save_selected_text(self) -> None:
        row = self.content_list.currentRow()
        if not 0 <= row < len(self._content) or not isinstance(self._content[row], str):
            return
        text = self.text_editor.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Texto vazio", "Escreva um texto antes de salvá-lo.")
            return
        self._content[row] = text
        self._refresh_items(row)
        self.status_label.setText("Texto atualizado. Salve a janela para aplicar ao manual.")

    def _add_text(self) -> None:
        text = self.text_editor.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Texto vazio", "Escreva um texto antes de adicioná-lo.")
            return
        row = self.content_list.currentRow()
        insert_at = row + 1 if row >= 0 else len(self._content)
        self._content.insert(insert_at, text)
        self._refresh_items(insert_at)
        self.status_label.setText("Novo bloco de texto inserido. Salve a janela para aplicar ao manual.")

    def _add_page(self) -> None:
        page = self.page_picker.currentData()
        if not isinstance(page, PdfPage):
            return
        row = self.content_list.currentRow()
        insert_at = row + 1 if row >= 0 else len(self._content)
        self._content.insert(insert_at, page)
        self._refresh_items(insert_at)
        self.status_label.setText("Página/recorte inserido. Salve a janela para aplicar ao manual.")

    def _remove_selected_item(self) -> None:
        row = self.content_list.currentRow()
        if not 0 <= row < len(self._content):
            return
        self._content.pop(row)
        self._refresh_items(row)
        self.status_label.setText("Item removido. Salve a janela para aplicar ao manual.")

    def _move_selected_item(self, direction: int) -> None:
        row = self.content_list.currentRow()
        destination = row + direction
        if direction not in {-1, 1} or not 0 <= row < len(self._content):
            return
        if not 0 <= destination < len(self._content):
            return
        self._content[row], self._content[destination] = (
            self._content[destination],
            self._content[row],
        )
        self._refresh_items(destination)
        self.status_label.setText("Ordem atualizada. Salve a janela para aplicar ao manual.")
