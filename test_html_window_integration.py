from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtWidgets import QApplication

from manual_builder.html_service import HtmlRenderService
from manual_builder.main_window import MainWindow


SAMPLE_HTML = """<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>Technical Manual</title></head>
<body>
  <h1>Motor Contactor 3RT2</h1>
  <p>Technical data and operating conditions.</p>
  <h2>Safety</h2>
  <p>Disconnect the equipment before maintenance.</p>
  <img src="diagram.png" alt="Contactor connection diagram">
  <h3>Maintenance</h3>
  <p>Inspect the terminals every six months.</p>
</body>
</html>"""


def main() -> None:
    app = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory(prefix="e2ps_html_window_test_") as temporary:
        root = Path(temporary)
        source = root / "manual.html"
        source.write_text(SAMPLE_HTML, encoding="utf-8")

        service = HtmlRenderService()
        pages = service.render(source, root / "rendered", lambda _current, _total: None)
        plan = service.analyze_structure(source)

        window = MainWindow()
        action_texts = [action.text() for action in window.findChildren(type(window.save_project_action))]
        assert "Open HTML" in action_texts, "A ação Open HTML não foi criada na barra de ferramentas."
        assert "HTML" in window.preview.text(), "A pré-visualização não orienta a abertura de HTML."

        window._html_rendering_completed(pages, plan)

        assert window.title_input.text() == "Motor Contactor 3RT2"
        assert len(window._sections) == 2, "A hierarquia HTML não gerou as seções esperadas."
        assert window._sections[1].title == "Safety"
        assert window._sections[1].subsections[0].title == "Maintenance"
        assert any(
            "Imagem encontrada: Contactor connection diagram" in block
            for block in window._sections[1].content
            if isinstance(block, str)
        ), "O aviso de captura da imagem não foi inserido na seção editável."
        assert window.section_tree.topLevelItemCount() == 2
        assert window.export_button.isEnabled(), "A exportação não foi habilitada após criar seções HTML."
        assert "2 seção(ões) editáveis" in window.chat_display.toPlainText()

        safety_item = window.section_tree.topLevelItem(1)
        window.section_tree.setCurrentItem(safety_item)
        window.content_text_input.setPlainText("Observação adicionada depois da importação.")
        window.add_text_block()
        assert "Observação adicionada depois da importação." in window._sections[1].content

        safety_item = window.section_tree.topLevelItem(1)
        window.section_tree.setCurrentItem(safety_item)
        window.subsection_name.setText("Notas adicionais")
        window.add_subsection()
        assert window._sections[1].subsections[-1].title == "Notas adicionais"

        window.close()

    app.quit()
    print("HTML window integration test passed")


if __name__ == "__main__":
    main()
