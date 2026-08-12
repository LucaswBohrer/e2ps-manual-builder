"""Data models used across the application."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class PdfPage:
    """A PDF page with independent export and thumbnail images."""

    number: int
    image_path: Path
    thumbnail_path: Path
    variant: int = 1

    @property
    def filename(self) -> str:
        """Return the standard image filename used in generated projects."""
        suffix = "" if self.variant == 1 else f"_crop_{self.variant:02d}"
        return f"page_{self.number:03d}{suffix}.png"

    @property
    def display_name(self) -> str:
        """Return a short human-readable label for selection controls."""
        if self.variant == 1:
            return f"Page {self.number:03d}"
        return f"Page {self.number:03d} · Crop {self.variant:02d}"


@dataclass(slots=True)
class ManualSubsection:
    """A user-named subsection that owns selected PDF page variants and optional descriptive text."""

    title: str
    pages: list[PdfPage]
    text_content: str = ""


@dataclass(slots=True)
class ManualSection:
    """A user-named manual section associated with selected PDF pages and optional descriptive text."""

    title: str
    pages: list[PdfPage]
    subsections: list[ManualSubsection] = field(default_factory=list)
    text_content: str = ""
