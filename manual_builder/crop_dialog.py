"""Interactive image crop dialog with zoom and precise source-pixel selection."""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QMouseEvent, QPixmap, QWheelEvent
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRubberBand,
    QScrollArea,
    QSlider,
    QVBoxLayout,
)


class CropImageLabel(QLabel):
    """Display a source image at different zoom levels and map selections to pixels."""

    zoomRequested = Signal(int)

    def __init__(self, source: QPixmap) -> None:
        super().__init__()
        self._source = source
        self._origin = QPoint()
        self._selection_source_rect = QRect()
        self._rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self)
        self._zoom_factor = 1.0
        self._fit_scale = self._calculate_fit_scale()
        self._scroll_area: QScrollArea | None = None
        self._pan_origin: QPoint | None = None
        self._pan_scroll_start: tuple[int, int] | None = None
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setMouseTracking(True)
        self._render_preview()

    def _calculate_fit_scale(self) -> float:
        """Return the initial scale used to keep the whole page comfortably visible."""
        if self._source.isNull() or self._source.width() <= 0 or self._source.height() <= 0:
            return 1.0
        return min(
            1000.0 / self._source.width(),
            700.0 / self._source.height(),
            1.0,
        )

    @property
    def zoom_factor(self) -> float:
        """Return the zoom relative to the initial fit-to-view scale."""
        return self._zoom_factor

    def set_scroll_area(self, scroll_area: QScrollArea) -> None:
        """Attach the scroll area so middle-button dragging can pan the zoomed page."""
        self._scroll_area = scroll_area

    def set_zoom_factor(self, value: float) -> None:
        """Set zoom relative to fit view, clamped to a useful precision range."""
        self._zoom_factor = max(0.25, min(float(value), 8.0))
        self._render_preview()

    def _display_scale(self) -> float:
        return max(0.0001, self._fit_scale * self._zoom_factor)

    def _render_preview(self) -> None:
        """Render the source at the current zoom while retaining the source selection."""
        if self._source.isNull():
            self.clear()
            self.setFixedSize(QSize())
            return
        scale = self._display_scale()
        display_size = QSize(
            max(1, round(self._source.width() * scale)),
            max(1, round(self._source.height() * scale)),
        )
        preview = self._source.scaled(
            display_size,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(preview)
        self.setFixedSize(preview.size())
        self._sync_rubber_band()

    def _clamp_display_point(self, point: QPoint) -> QPoint:
        """Clamp a label-local point to the visible image bounds."""
        if self.pixmap() is None:
            return QPoint()
        return QPoint(
            max(0, min(point.x(), self.pixmap().width() - 1)),
            max(0, min(point.y(), self.pixmap().height() - 1)),
        )

    def _display_point_to_source(self, point: QPoint) -> QPoint:
        """Convert a label-local display point into original source pixels."""
        point = self._clamp_display_point(point)
        scale = self._display_scale()
        return QPoint(
            max(0, min(round(point.x() / scale), self._source.width() - 1)),
            max(0, min(round(point.y() / scale), self._source.height() - 1)),
        )

    def _display_rect_to_source_rect(self, rectangle: QRect) -> QRect:
        """Convert a display selection to a bounded rectangle in source pixels."""
        if rectangle.isNull() or self.pixmap() is None:
            return QRect()
        rectangle = rectangle.normalized()
        top_left = self._display_point_to_source(rectangle.topLeft())
        bottom_right = self._display_point_to_source(rectangle.bottomRight())
        source_rect = QRect(
            top_left,
            QSize(
                max(1, bottom_right.x() - top_left.x() + 1),
                max(1, bottom_right.y() - top_left.y() + 1),
            ),
        )
        return source_rect.intersected(self._source.rect())

    def source_to_display_rect(self, rectangle: QRect) -> QRect:
        """Convert a source-pixel rectangle into the current display coordinates."""
        if rectangle.isNull() or self.pixmap() is None:
            return QRect()
        scale = self._display_scale()
        return QRect(
            round(rectangle.x() * scale),
            round(rectangle.y() * scale),
            max(1, round(rectangle.width() * scale)),
            max(1, round(rectangle.height() * scale)),
        ).intersected(self.rect())

    def _update_selection_from_display_rect(self, rectangle: QRect) -> None:
        """Update the source selection while the user is dragging."""
        source_rect = self._display_rect_to_source_rect(rectangle)
        self._selection_source_rect = source_rect
        self._sync_rubber_band()

    def _sync_rubber_band(self) -> None:
        """Place the visual selection over the image after zoom or selection changes."""
        if self._selection_source_rect.isNull() or self.pixmap() is None:
            self._rubber_band.hide()
            return
        display_rect = self.source_to_display_rect(self._selection_source_rect)
        if display_rect.width() < 2 or display_rect.height() < 2:
            self._rubber_band.hide()
            return
        self._rubber_band.setGeometry(display_rect)
        self._rubber_band.show()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Begin a crop rectangle or pan the zoomed page."""
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_origin = event.position().toPoint()
            if self._scroll_area is not None:
                self._pan_scroll_start = (
                    self._scroll_area.horizontalScrollBar().value(),
                    self._scroll_area.verticalScrollBar().value(),
                )
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._origin = self._clamp_display_point(event.position().toPoint())
            self._selection_source_rect = QRect()
            self._rubber_band.setGeometry(QRect(self._origin, QSize()))
            self._rubber_band.show()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Resize the crop rectangle or pan while the corresponding button is held."""
        position = event.position().toPoint()
        if self._pan_origin is not None and self._scroll_area is not None:
            delta = position - self._pan_origin
            start_horizontal, start_vertical = self._pan_scroll_start or (0, 0)
            self._scroll_area.horizontalScrollBar().setValue(start_horizontal - delta.x())
            self._scroll_area.verticalScrollBar().setValue(start_vertical - delta.y())
            event.accept()
            return
        if self._rubber_band.isVisible() and (event.buttons() & Qt.MouseButton.LeftButton):
            self._update_selection_from_display_rect(QRect(self._origin, position).normalized())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Finish panning or commit the final crop rectangle."""
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_origin = None
            self._pan_scroll_start = None
            self.setCursor(Qt.CursorShape.CrossCursor)
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._update_selection_from_display_rect(
                QRect(self._origin, event.position().toPoint()).normalized()
            )
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Use Ctrl + mouse wheel as a quick precision zoom shortcut."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = 25 if event.angleDelta().y() > 0 else -25
            self.zoomRequested.emit(delta)
            event.accept()
            return
        super().wheelEvent(event)

    def selected_source_rect(self) -> QRect:
        """Return the selection in original, full-resolution image coordinates."""
        return QRect(self._selection_source_rect)


class CropDialog(QDialog):
    """Modal crop editor with zoom controls and precise source-pixel selection."""

    def __init__(self, source: QPixmap, parent: object | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Recortar página — zoom")
        self.resize(1050, 820)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Arraste para selecionar a área que deseja manter. "
                "Use os controles de zoom ou Ctrl + roda do mouse para ver detalhes. "
                "Com o botão do meio, arraste para navegar pela página ampliada."
            )
        )

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Zoom:"))
        self._zoom_out_button = QPushButton("−")
        self._zoom_out_button.setToolTip("Diminuir zoom")
        self._zoom_out_button.clicked.connect(lambda: self._change_zoom(-25))
        controls.addWidget(self._zoom_out_button)

        self._zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self._zoom_slider.setRange(25, 800)
        self._zoom_slider.setSingleStep(25)
        self._zoom_slider.setPageStep(100)
        self._zoom_slider.setValue(100)
        self._zoom_slider.setMinimumWidth(260)
        self._zoom_slider.valueChanged.connect(self._set_zoom_percent)
        controls.addWidget(self._zoom_slider, 1)

        self._zoom_value_label = QLabel("100%")
        self._zoom_value_label.setMinimumWidth(48)
        controls.addWidget(self._zoom_value_label)

        self._zoom_in_button = QPushButton("+")
        self._zoom_in_button.setToolTip("Aumentar zoom")
        self._zoom_in_button.clicked.connect(lambda: self._change_zoom(25))
        controls.addWidget(self._zoom_in_button)

        fit_button = QPushButton("Ajustar página")
        fit_button.setToolTip("Voltar a mostrar a página inteira")
        fit_button.clicked.connect(lambda: self._zoom_slider.setValue(100))
        controls.addWidget(fit_button)
        layout.addLayout(controls)

        self._image_label = CropImageLabel(source)
        scroll_area = QScrollArea()
        scroll_area.setWidget(self._image_label)
        scroll_area.setWidgetResizable(False)
        scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._image_label.set_scroll_area(scroll_area)
        self._image_label.zoomRequested.connect(self._change_zoom)
        layout.addWidget(scroll_area, 1)
        self._scroll_area = scroll_area

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Apply
        )
        buttons.rejected.connect(self.reject)
        cancel_button = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_button is not None:
            cancel_button.setText("Cancelar")
        apply_button = buttons.button(QDialogButtonBox.StandardButton.Apply)
        if apply_button is not None:
            apply_button.setText("Aplicar recorte")
            apply_button.clicked.connect(self._apply_crop)
        layout.addWidget(buttons)

    def _change_zoom(self, delta_percent: int) -> None:
        """Change zoom by a control step without leaving the slider range."""
        self._zoom_slider.setValue(self._zoom_slider.value() + delta_percent)

    def _visible_source_center(self) -> QPoint:
        """Return the source point currently at the center of the scroll viewport."""
        viewport = self._scroll_area.viewport()
        display_center = QPoint(
            self._scroll_area.horizontalScrollBar().value() + viewport.width() // 2,
            self._scroll_area.verticalScrollBar().value() + viewport.height() // 2,
        )
        return self._image_label._display_point_to_source(display_center)

    def _restore_visible_source_center(self, source_center: QPoint) -> None:
        """Keep the same source region visible after a zoom change."""
        scale = self._image_label._display_scale()
        display_center = QPoint(
            round(source_center.x() * scale),
            round(source_center.y() * scale),
        )
        viewport = self._scroll_area.viewport()
        self._scroll_area.horizontalScrollBar().setValue(
            max(0, display_center.x() - viewport.width() // 2)
        )
        self._scroll_area.verticalScrollBar().setValue(
            max(0, display_center.y() - viewport.height() // 2)
        )

    def _set_zoom_percent(self, percent: int) -> None:
        """Apply a slider value and preserve the user's current area of interest."""
        source_center = self._visible_source_center()
        self._image_label.set_zoom_factor(percent / 100.0)
        self._zoom_value_label.setText(f"{percent}%")
        QTimer.singleShot(0, lambda: self._restore_visible_source_center(source_center))

    def _apply_crop(self) -> None:
        """Accept only after a valid crop area was selected."""
        if not self.selected_rect().isNull():
            self.accept()

    def selected_rect(self) -> QRect:
        """Return the crop rectangle in original image pixels."""
        return self._image_label.selected_source_rect()
