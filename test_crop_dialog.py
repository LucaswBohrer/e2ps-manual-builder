from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRect
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication

from manual_builder.crop_dialog import CropImageLabel


def _application() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_crop_selection_maps_to_original_pixels_at_fit_zoom() -> None:
    _application()
    source = QPixmap(1600, 1200)
    label = CropImageLabel(source)

    label._update_selection_from_display_rect(QRect(100, 100, 200, 150))
    selected = label.selected_source_rect()

    assert selected.x() == round(100 / label._display_scale())
    assert selected.y() == round(100 / label._display_scale())
    assert selected.width() > 300
    assert selected.height() > 200


def test_zoom_preserves_selection_in_source_coordinates() -> None:
    _application()
    source = QPixmap(1600, 1200)
    label = CropImageLabel(source)
    label._update_selection_from_display_rect(QRect(100, 100, 200, 150))
    before = label.selected_source_rect()

    label.set_zoom_factor(3.0)
    after = label.selected_source_rect()

    assert after == before
    display_rect = label.source_to_display_rect(after)
    assert display_rect.width() > before.width()
    assert display_rect.height() > before.height()


def test_zoomed_drag_maps_a_small_display_area_to_a_precise_source_area() -> None:
    _application()
    source = QPixmap(2400, 1600)
    label = CropImageLabel(source)
    label.set_zoom_factor(4.0)

    label._update_selection_from_display_rect(QRect(400, 300, 40, 32))
    selected = label.selected_source_rect()

    assert selected.width() >= 9
    assert selected.height() >= 7
    assert selected.right() < source.width()
    assert selected.bottom() < source.height()
