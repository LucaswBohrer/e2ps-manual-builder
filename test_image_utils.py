from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PIL import Image
from PySide6.QtWidgets import QApplication

from manual_builder.image_utils import convert_image_to_png


def _application() -> QApplication:
    return QApplication.instance() or QApplication([])


def _assert_png(path, size: tuple[int, int]) -> None:
    with Image.open(path) as converted:
        assert converted.format == "PNG"
        assert converted.size == size


def test_raster_content_is_decoded_even_with_unknown_extension(tmp_path) -> None:
    source = tmp_path / "capa.arquivo_desconhecido"
    destination = tmp_path / "Capa.png"
    Image.new("RGBA", (320, 180), (20, 100, 200, 128)).save(source, format="PNG")

    assert convert_image_to_png(source, destination) == destination
    _assert_png(destination, (320, 180))
    with Image.open(destination) as converted:
        assert converted.mode == "RGBA"


def test_webp_content_is_decoded_even_with_unknown_extension(tmp_path) -> None:
    source = tmp_path / "capa.sem_extensao"
    destination = tmp_path / "Capa.png"
    Image.new("RGB", (240, 140), "#e07826").save(source, format="WEBP")

    convert_image_to_png(source, destination)
    _assert_png(destination, (240, 140))


def test_avif_content_is_decoded_when_pillow_supports_avif(tmp_path) -> None:
    if ".avif" not in {suffix.lower() for suffix in Image.registered_extensions()}:
        pytest.skip("Pillow sem suporte AVIF nesta plataforma")
    source = tmp_path / "capa.formato_customizado"
    destination = tmp_path / "Capa.png"
    Image.new("RGB", (180, 100), "#2c9b62").save(source, format="AVIF")

    convert_image_to_png(source, destination)
    _assert_png(destination, (180, 100))


def test_svg_content_is_rendered_even_with_unknown_extension(tmp_path) -> None:
    _application()
    source = tmp_path / "capa.vetor"
    destination = tmp_path / "Capa.png"
    source.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="420" height="210">'
        '<rect width="420" height="210" fill="#143d59"/>'
        '<circle cx="210" cy="105" r="70" fill="#f4b41a"/>'
        '</svg>',
        encoding="utf-8",
    )

    convert_image_to_png(source, destination)
    _assert_png(destination, (420, 210))


def test_random_file_is_rejected_with_a_clear_error(tmp_path) -> None:
    source = tmp_path / "capa.qualquer_coisa"
    source.write_bytes(b"not an image")

    with pytest.raises(ValueError, match="does not contain a supported image"):
        convert_image_to_png(source, tmp_path / "Capa.png")


def test_main_window_cover_picker_accepts_arbitrary_extension(tmp_path, monkeypatch) -> None:
    from manual_builder.main_window import MainWindow

    _application()
    source = tmp_path / "manual_cover.custom"
    Image.new("RGB", (260, 160), "#5d2e8c").save(source, format="WEBP")
    monkeypatch.setattr(
        "manual_builder.main_window.QFileDialog.getOpenFileName",
        lambda *_args, **_kwargs: (str(source), "Todos os arquivos (*.*)"),
    )

    window = MainWindow()
    try:
        window._browse_cover_image()
        assert window._cover_image_path is not None
        assert window._cover_image_path.suffix == ".png"
        assert window._cover_image_path.is_file()
        assert "manual_cover.custom" in window.cover_path_input.text()
        _assert_png(window._cover_image_path, (260, 160))
    finally:
        window.close()


def test_export_service_normalizes_non_png_cover_to_capa_png(tmp_path) -> None:
    from manual_builder.project_service import ProjectExportService

    source = tmp_path / "cover.legacy_asset"
    Image.new("RGB", (200, 120), "#b83280").save(source, format="WEBP")

    project_dir = ProjectExportService().export(
        tmp_path / "exported",
        "Manual com capa legada",
        [],
        cover_image_path=source,
    )
    capa = project_dir / "Capa.png"
    assert capa.is_file()
    _assert_png(capa, (200, 120))
