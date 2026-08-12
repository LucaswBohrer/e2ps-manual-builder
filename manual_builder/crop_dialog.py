"""Interactive image crop dialog used before exporting manual pages."""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtGui import QMouseEvent, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QRubberBand,
    QScrollArea,
    QVBoxLayout,
)


class CropImageLabel(QLabel):
    """Show a scaled image and translate a selection to source pixels."""

    def __init__(self, source: QPixmap) -> None:
        super().__init__()
        self._source = source
        self._origin = QPoint()
        self._rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self)
        self.setCursor(Qt.CursorShape.CrossCursor)
        preview = source.scaled(
            QSize(1000, 700),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(preview)
        self.setFixedSize(preview.size())

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Begin a crop rectangle on a left click."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._origin = event.position().toPoint()
            self._rubber_band.setGeometry(QRect(self._origin, QSize()))
            self._rubber_band.show()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Resize the crop rectangle as the user drags."""
        if self._rubber_band.isVisible():
            self._rubber_band.setGeometry(
                QRect(self._origin, event.position().toPoint()).normalized()
            )

    def selected_source_rect(self) -> QRect:
        """Return the selection in original, full-resolution image coordinates."""
        rectangle = self._rubber_band.geometry()
        preview = self.pixmap()
        if rectangle.width() < 2 or rectangle.height() < 2 or preview is None:
            return QRect()
        scale_x = self._source.width() / preview.width()
        scale_y = self._source.height() / preview.height()
        source_rect = QRect(
            round(rectangle.x() * scale_x),
            round(rectangle.y() * scale_y),
            round(rectangle.width() * scale_x),
            round(rectangle.height() * scale_y),
        )
        return source_rect.intersected(self._source.rect())


class CropDialog(QDialog):
    """Modal crop editor where users select the visible area to preserve."""

    def __init__(self, source: QPixmap, parent: object | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Crop PDF Page")
        self.resize(1050, 820)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Drag over the area to keep, then select Apply."))
        self._image_label = CropImageLabel(source)
        scroll_area = QScrollArea()
        scroll_area.setWidget(self._image_label)
        scroll_area.setWidgetResizable(False)
        layout.addWidget(scroll_area)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Apply
        )
        buttons.rejected.connect(self.reject)
        apply_button = buttons.button(QDialogButtonBox.StandardButton.Apply)
        if apply_button is not None:
            apply_button.clicked.connect(self._apply_crop)
        layout.addWidget(buttons)

    def _apply_crop(self) -> None:
        """Accept only after a valid crop area was selected."""
        if not self.selected_rect().isNull():
            self.accept()

    def selected_rect(self) -> QRect:
        """Return the crop rectangle in original image pixels."""
        return self._image_label.selected_source_rect()
