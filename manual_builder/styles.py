"""Centralized application visual theme."""

DARK_STYLESHEET = """
QWidget { background: #171a21; color: #e6e9ef; font-family: Segoe UI, Arial; font-size: 13px; }
QMainWindow { background: #171a21; }
QToolBar { background: #20242d; border: none; padding: 9px; spacing: 8px; }
QPushButton { background: #f59e0b; color: #181818; border: 0; border-radius: 6px; padding: 8px 14px; font-weight: 600; }
QPushButton:hover { background: #fbbf24; }
QPushButton:disabled { background: #4b4f58; color: #9ca3af; }
QListWidget { background: #20242d; border: 1px solid #323844; border-radius: 6px; padding: 5px; }
QListWidget::item { padding: 8px; border-radius: 4px; }
QListWidget::item:selected { background: #384152; }
QLabel#preview { background: #101217; border: 1px solid #323844; border-radius: 8px; }
QProgressBar { border: 1px solid #3b4252; border-radius: 5px; text-align: center; background: #20242d; }
QProgressBar::chunk { background: #f59e0b; border-radius: 4px; }
QLineEdit { background: #20242d; border: 1px solid #3b4252; border-radius: 5px; padding: 7px; }
QStatusBar { background: #20242d; color: #aab2c0; }
"""
