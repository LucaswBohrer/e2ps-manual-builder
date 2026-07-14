"""Data models used across the application."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class PdfPage:
    """A PDF page with independent export and thumbnail images."""

    number: int
    image_path: Path
    thumbnail_path: Path

    @property
    def filename(self) -> str:
        """Return the standard image filename used in generated projects."""
        return f"page_{self.number:03d}.png"


@dataclass(slots=True)
class ManualSection:
    """A user-named manual section associated with selected PDF pages."""

    title: str
    pages: list[PdfPage]
