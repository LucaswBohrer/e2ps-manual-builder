"""Application entry point for E2PS Manual Builder."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from manual_builder.main_window import MainWindow
from manual_builder.styles import DARK_STYLESHEET


def main() -> int:
    """Start the Qt application."""
    app = QApplication(sys.argv)
    app.setApplicationName("E2PS Manual Builder")
    app.setStyleSheet(DARK_STYLESHEET)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
