from __future__ import annotations

from PySide6.QtWidgets import QApplication

from manual_builder.main_window import MainWindow


def main() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    action_texts = [action.text() for action in window.findChildren(type(window.save_project_action))]
    assert "Open HTML" in action_texts, "A ação Open HTML não foi criada na barra de ferramentas."
    assert "HTML" in window.preview.text(), "A pré-visualização não orienta a abertura de HTML."
    window.close()
    app.quit()
    print("HTML window integration test passed")


if __name__ == "__main__":
    main()
