"""Application entry point for E2PS Manual Builder."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QSettings, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from manual_builder.main_window import MainWindow
from manual_builder.styles import THEME_DARK, THEME_LIGHT, stylesheet_for_theme


def main() -> int:
    """Start the Qt application."""
    app = QApplication(sys.argv)
    app.setApplicationName("E2PS Manual Builder")
    icon_path = Path(__file__).resolve().parent / "manual_builder" / "assets" / "e2ps.ico"
    if icon_path.is_file():
        app.setWindowIcon(QIcon(str(icon_path)))
    settings = QSettings("E2PS", "ManualBuilder")
    saved_theme = str(settings.value("ui/theme", THEME_LIGHT) or THEME_LIGHT).strip().lower()
    if saved_theme not in {THEME_LIGHT, THEME_DARK}:
        saved_theme = THEME_LIGHT
    app.setStyleSheet(stylesheet_for_theme(saved_theme))
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
