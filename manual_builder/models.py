"""Data models used across the application."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Union


@dataclass(frozen=True, slots=True)
class PdfPage:
    """A PDF page with independent export, thumbnail images and extracted text content."""

    number: int
    image_path: Path
    thumbnail_path: Path
    variant: int = 1
    extracted_text: str = ""
    export_mode: str = "image"  # "image" or "text"
    source_type: str = "pdf"  # "pdf", "image" or "html"

    @property
    def filename(self) -> str:
        """Return the standard image filename used in generated projects."""
        suffix = "" if self.variant == 1 else f"_crop_{self.variant:02d}"
        return f"page_{self.number:03d}{suffix}.png"

    @property
    def display_name(self) -> str:
        """Return a short human-readable label for selection controls."""
        source_label = "HTML " if self.source_type == "html" else ""
        if self.variant == 1:
            return f"{source_label}Page {self.number:03d}"
        return f"{source_label}Page {self.number:03d} · Crop {self.variant:02d}"


@dataclass(slots=True)
class ManualSubsection:
    """A user-named subsection that owns mixed content blocks (PdfPage or text snippets)."""

    title: str
    content: list[Union[PdfPage, str]] = field(default_factory=list)


@dataclass(slots=True)
class ManualSection:
    """A user-named manual section associated with mixed content blocks and subsections."""

    title: str
    content: list[Union[PdfPage, str]] = field(default_factory=list)
    subsections: list[ManualSubsection] = field(default_factory=list)
