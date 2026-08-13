from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtWidgets import QApplication

from manual_builder.html_service import HtmlRenderService


SAMPLE_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Technical Manual</title>
  <style>body { font-family: Arial; } table { width: 100%; }</style>
</head>
<body>
  <h1>Motor Contactor 3RT2</h1>
  <p>Technical data and operating conditions.</p>
  <table>
    <tr><th>Rated voltage</th><th>690 V</th></tr>
    <tr><td>Operational current</td><td>22 A</td></tr>
  </table>
  <h2>Safety</h2>
  <p>Disconnect the equipment before maintenance.</p>
</body>
</html>"""


def main() -> None:
    app = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory(prefix="e2ps_html_test_") as temporary:
        root = Path(temporary)
        source = root / "manual.html"
        source.write_text(SAMPLE_HTML, encoding="utf-8")
        progress: list[tuple[int, int]] = []
        pages = HtmlRenderService().render(
            source,
            root / "rendered",
            lambda current, total: progress.append((current, total)),
        )

        assert pages, "O HTML não gerou nenhuma página."
        assert all(page.image_path.is_file() for page in pages), "Uma página PNG não foi criada."
        assert all(page.thumbnail_path.is_file() for page in pages), "Uma miniatura não foi criada."
        assert all(page.source_type == "html" for page in pages), "A origem HTML não foi preservada."
        extracted = "\n".join(page.extracted_text for page in pages)
        assert "Motor Contactor" in extracted and "Rated voltage" in extracted
        assert progress and progress[-1] == (len(pages), len(pages))

    app.quit()
    print("HTML import test passed")


if __name__ == "__main__":
    main()
