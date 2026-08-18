"""Utilities for normalizing user-provided images to PNG assets."""

from __future__ import annotations

import re
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError:  # pragma: no cover - the packaged application includes Pillow.
    Image = None
    ImageOps = None


_SVG_MARKER = re.compile(rb"<svg(?:\s|>)", re.IGNORECASE)


def _looks_like_svg(raw: bytes) -> bool:
    """Recognize SVG by its content instead of trusting the filename extension."""
    return bool(_SVG_MARKER.search(raw[:65536]))


def _save_svg_as_png(raw: bytes, destination: Path) -> None:
    """Render SVG bytes to a PNG without requiring the source to end in `.svg`."""
    try:
        from PySide6.QtCore import QByteArray, QSize
        from PySide6.QtGui import QImage, QPainter
        from PySide6.QtSvg import QSvgRenderer
    except Exception as error:  # pragma: no cover - exercised only on incomplete installs.
        raise ValueError("O suporte a SVG não está disponível nesta instalação.") from error

    renderer = QSvgRenderer(QByteArray(raw))
    if not renderer.isValid():
        raise ValueError("O arquivo parece SVG, mas não contém uma imagem SVG válida.")

    size = renderer.defaultSize()
    if not size.isValid() or size.width() <= 0 or size.height() <= 0:
        size = QSize(1600, 1000)
    image = QImage(size, QImage.Format.Format_ARGB32)
    image.fill(0)
    painter = QPainter(image)
    try:
        renderer.render(painter)
    finally:
        painter.end()
    if not image.save(str(destination), "PNG"):
        raise OSError("Não foi possível salvar a capa convertida para PNG.")


def convert_image_to_png(source: Path, destination: Path) -> Path:
    """Decode an image by its bytes and write a normalized PNG destination.

    The source extension is deliberately ignored. Pillow handles common raster formats
    including AVIF and WebP, while QtSvg handles SVG content even when the file has an
    arbitrary extension. The source is never modified.
    """
    source = Path(source)
    destination = Path(destination)
    if not source.is_file():
        raise FileNotFoundError(f"A imagem de capa não foi encontrada: {source}")
    if source.stat().st_size == 0:
        raise ValueError("O arquivo escolhido para a capa está vazio.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    raw = source.read_bytes()

    pillow_error: Exception | None = None
    if Image is not None:
        try:
            with Image.open(source) as opened:
                opened.load()
                image = ImageOps.exif_transpose(opened) if ImageOps is not None else opened.copy()
                if image.mode in {"RGBA", "LA"} or (
                    image.mode == "P" and "transparency" in image.info
                ):
                    normalized = image.convert("RGBA")
                else:
                    normalized = image.convert("RGB")
                normalized.save(destination, "PNG", optimize=True)
                normalized.close()
            return destination
        except Exception as error:
            pillow_error = error

    if _looks_like_svg(raw):
        _save_svg_as_png(raw, destination)
        return destination

    detail = f" ({pillow_error})" if pillow_error else ""
    raise ValueError(
        "O arquivo selecionado não contém uma imagem compatível. "
        "A extensão pode ser qualquer uma, mas o conteúdo precisa ser uma imagem válida "
        f"(PNG, JPEG, WebP, AVIF, SVG ou outro formato suportado){detail}."
    )
