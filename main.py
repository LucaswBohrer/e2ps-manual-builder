"""Application entry point for E2PS Manual Builder."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from manual_builder.main_window import MainWindow
from manual_builder.styles import DARK_STYLESHEET


def main() -> int:
    """Start the Qt application."""
    app = QApplication(sys.argv)
    app.setApplicationName("E2PS Manual Builder")
    icon_path = Path(__file__).resolve().parent / "manual_builder" / "assets" / "e2ps.ico"
    if icon_path.is_file():
        app.setWindowIcon(QIcon(str(icon_path)))
    app.setStyleSheet(DARK_STYLESHEET)
    window = MainWindow()
    window.show()

    # The Windows installer associates .e2ps/.emb files with this executable.
    # Deferring the load until the event loop begins ensures errors are displayed
    # in the already-visible application window.
    for argument in sys.argv[1:]:
        project_path = Path(argument)
        if project_path.is_file() and project_path.suffix.lower() in {".e2ps", ".emb"}:
            QTimer.singleShot(0, lambda path=project_path: window.open_e2ps_project_file(path))
            break
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
