"""Application-wide visual themes for the E2PS Manual Builder V2."""

THEME_LIGHT = "light"
THEME_DARK = "dark"

LIGHT_STYLESHEET = """
QWidget {
    background: #F4F7FA;
    color: #17324D;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}
QMainWindow {
    background: #F4F7FA;
}
QToolBar {
    background: #FFFFFF;
    border: 0;
    border-bottom: 1px solid #D7E2EA;
    padding: 8px;
    spacing: 7px;
}
QToolBar::separator {
    background: #D7E2EA;
    width: 1px;
    margin: 4px 5px;
}
QGroupBox {
    background: #FFFFFF;
    border: 1px solid #D7E2EA;
    border-radius: 8px;
    margin-top: 12px;
    padding: 12px 8px 8px 8px;
    font-weight: 600;
    color: #17324D;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #0B6E82;
    background: #F4F7FA;
}
QPushButton {
    background: #0B6E82;
    color: #FFFFFF;
    border: 0;
    border-radius: 6px;
    padding: 8px 12px;
    font-weight: 600;
}
QPushButton:hover {
    background: #095A6B;
}
QPushButton:pressed {
    background: #064654;
}
QPushButton:disabled {
    background: #D5DEE5;
    color: #7B8994;
}
QLineEdit, QTextEdit, QComboBox {
    background: #FFFFFF;
    color: #17324D;
    border: 1px solid #C5D4DE;
    border-radius: 5px;
    padding: 7px;
    selection-background-color: #BFE8EE;
    selection-color: #17324D;
}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
    border: 1px solid #0B6E82;
}
QComboBox QAbstractItemView {
    background: #FFFFFF;
    color: #17324D;
    selection-background-color: #DDF3F6;
    selection-color: #17324D;
}
QListWidget, QTreeWidget {
    background: #FFFFFF;
    color: #17324D;
    border: 1px solid #C5D4DE;
    border-radius: 6px;
    padding: 5px;
}
QListWidget::item, QTreeWidget::item {
    padding: 7px;
    border-radius: 4px;
}
QListWidget::item:selected, QTreeWidget::item:selected {
    background: #DDF3F6;
    color: #17324D;
}
QScrollArea {
    background: #EAF0F4;
    border: 0;
}
QLabel#preview {
    background: #EAF0F4;
    border: 1px solid #C5D4DE;
    border-radius: 8px;
    color: #607383;
}
QLabel#brand_title {
    color: #12304A;
    font-size: 20px;
    font-weight: 700;
}
QLabel#brand_subtitle {
    color: #607383;
    font-size: 12px;
}
QLabel#brand_badge {
    color: #FFFFFF;
    background: #F2A900;
    border-radius: 5px;
    padding: 6px 10px;
    font-weight: 700;
}
QWidget#brand_header {
    background: #FFFFFF;
    border: 1px solid #D7E2EA;
    border-radius: 9px;
}
QProgressBar {
    border: 1px solid #C5D4DE;
    border-radius: 5px;
    text-align: center;
    background: #FFFFFF;
    color: #17324D;
}
QProgressBar::chunk {
    background: #F2A900;
    border-radius: 4px;
}
QStatusBar {
    background: #FFFFFF;
    color: #607383;
    border-top: 1px solid #D7E2EA;
}
QSplitter::handle {
    background: #D7E2EA;
}
QMenu {
    background: #FFFFFF;
    color: #17324D;
    border: 1px solid #C5D4DE;
}
QMenu::item:selected {
    background: #DDF3F6;
}
QCheckBox {
    color: #17324D;
    spacing: 6px;
}
QCheckBox::indicator {
    width: 15px;
    height: 15px;
}
QToolTip {
    background: #17324D;
    color: #FFFFFF;
    border: 1px solid #0B6E82;
    padding: 5px;
}
"""

DARK_STYLESHEET = """
QWidget {
    background: #17232E;
    color: #E7F0F5;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}
QMainWindow {
    background: #17232E;
}
QToolBar {
    background: #1E303D;
    border: 0;
    border-bottom: 1px solid #355263;
    padding: 8px;
    spacing: 7px;
}
QToolBar::separator {
    background: #355263;
    width: 1px;
    margin: 4px 5px;
}
QGroupBox {
    background: #203440;
    border: 1px solid #355263;
    border-radius: 8px;
    margin-top: 12px;
    padding: 12px 8px 8px 8px;
    font-weight: 600;
    color: #E7F0F5;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #62D1D7;
    background: #17232E;
}
QPushButton {
    background: #0E8096;
    color: #FFFFFF;
    border: 0;
    border-radius: 6px;
    padding: 8px 12px;
    font-weight: 600;
}
QPushButton:hover {
    background: #119DB2;
}
QPushButton:pressed {
    background: #096478;
}
QPushButton:disabled {
    background: #40535F;
    color: #91A1AA;
}
QLineEdit, QTextEdit, QComboBox {
    background: #172A35;
    color: #E7F0F5;
    border: 1px solid #466474;
    border-radius: 5px;
    padding: 7px;
    selection-background-color: #0B6E82;
    selection-color: #FFFFFF;
}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
    border: 1px solid #62D1D7;
}
QComboBox QAbstractItemView {
    background: #203440;
    color: #E7F0F5;
    selection-background-color: #0B6E82;
    selection-color: #FFFFFF;
}
QListWidget, QTreeWidget {
    background: #172A35;
    color: #E7F0F5;
    border: 1px solid #466474;
    border-radius: 6px;
    padding: 5px;
}
QListWidget::item, QTreeWidget::item {
    padding: 7px;
    border-radius: 4px;
}
QListWidget::item:selected, QTreeWidget::item:selected {
    background: #0B6E82;
    color: #FFFFFF;
}
QScrollArea {
    background: #101A22;
    border: 0;
}
QLabel#preview {
    background: #101A22;
    border: 1px solid #466474;
    border-radius: 8px;
    color: #AEBFC8;
}
QLabel#brand_title {
    color: #F1FAFC;
    font-size: 20px;
    font-weight: 700;
}
QLabel#brand_subtitle {
    color: #AEBFC8;
    font-size: 12px;
}
QLabel#brand_badge {
    color: #17232E;
    background: #F2A900;
    border-radius: 5px;
    padding: 6px 10px;
    font-weight: 700;
}
QWidget#brand_header {
    background: #203440;
    border: 1px solid #355263;
    border-radius: 9px;
}
QProgressBar {
    border: 1px solid #466474;
    border-radius: 5px;
    text-align: center;
    background: #172A35;
    color: #E7F0F5;
}
QProgressBar::chunk {
    background: #F2A900;
    border-radius: 4px;
}
QStatusBar {
    background: #1E303D;
    color: #AEBFC8;
    border-top: 1px solid #355263;
}
QSplitter::handle {
    background: #355263;
}
QMenu {
    background: #203440;
    color: #E7F0F5;
    border: 1px solid #466474;
}
QMenu::item:selected {
    background: #0B6E82;
    color: #FFFFFF;
}
QCheckBox {
    color: #E7F0F5;
    spacing: 6px;
}
QCheckBox::indicator {
    width: 15px;
    height: 15px;
}
QToolTip {
    background: #E7F0F5;
    color: #17232E;
    border: 1px solid #62D1D7;
    padding: 5px;
}
"""


def stylesheet_for_theme(theme: str) -> str:
    """Return the application stylesheet for a persisted theme name."""
    return DARK_STYLESHEET if str(theme).strip().lower() == THEME_DARK else LIGHT_STYLESHEET


# Backward-compatible default name used by older integrations.
DEFAULT_STYLESHEET = LIGHT_STYLESHEET
