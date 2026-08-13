from __future__ import annotations

import math
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QRectF, QSize, Qt, QUrl
from PySide6.QtGui import QColor, QImage, QPainter, QTextDocument

from manual_builder.models import PdfPage


class _VisibleTextExtractor(HTMLParser):
    """Extract human-readable text from an HTML document without scripts or styles."""

    _IGNORED_TAGS = {"script", "style", "noscript", "template", "svg"}
    _BREAK_TAGS = {
        "address", "article", "aside", "blockquote", "br", "caption", "dd", "div", "dt",
        "figcaption", "footer", "h1", "h2", "h3", "h4", "h5", "h6", "header", "li",
        "main", "p", "section", "table", "td", "th", "tr",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._ignored_depth = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized = tag.lower()
        if normalized in self._IGNORED_TAGS:
            self._ignored_depth += 1
        elif not self._ignored_depth and normalized in self._BREAK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()
        if normalized in self._IGNORED_TAGS and self._ignored_depth:
            self._ignored_depth -= 1
        elif not self._ignored_depth and normalized in self._BREAK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            self._parts.append(data)

    def text(self) -> str:
        lines = [re.sub(r"\s+", " ", line).strip() for line in "".join(self._parts).splitlines()]
        return "\n".join(line for line in lines if line)


class HtmlRenderService:
    """Render static HTML files to PNG pages and retain their readable source text.

    The renderer intentionally uses Qt's built-in rich-text engine, avoiding a new browser
    or system dependency. It supports static HTML, tables, images, inline styles and local
    assets. JavaScript-generated content and advanced browser-only CSS are not executed.
    """

    PAGE_WIDTH = 1240
    PAGE_HEIGHT = 1754
    MARGIN = 56
    THUMBNAIL_SIZE = QSize(170, 170)

    @staticmethod
    def _read_html(source: Path) -> str:
        raw = source.read_bytes()
        declared = re.search(
            br"<meta[^>]+charset=[\"']?\s*([a-zA-Z0-9._-]+)", raw[:4096], re.IGNORECASE
        )
        encodings = [declared.group(1).decode("ascii", errors="ignore")] if declared else []
        encodings.extend(["utf-8", "utf-8-sig", "latin-1"])
        for encoding in dict.fromkeys(encoding for encoding in encodings if encoding):
            try:
                return raw.decode(encoding)
            except (LookupError, UnicodeDecodeError):
                continue
        return raw.decode("utf-8", errors="replace")

    @staticmethod
    def _extract_text(html: str) -> str:
        parser = _VisibleTextExtractor()
        parser.feed(html)
        parser.close()
        return parser.text()

    @classmethod
    def _text_for_page(cls, full_text: str, page_index: int, page_count: int) -> str:
        """Split source text approximately by visual page for AI context and project persistence."""
        if not full_text:
            return ""
        if page_count <= 1:
            return full_text
        chunk_size = max(1, math.ceil(len(full_text) / page_count))
        start = page_index * chunk_size
        end = min(len(full_text), start + chunk_size)
        return full_text[start:end].strip()

    def render(
        self,
        source: Path,
        destination: Path,
        on_progress: Callable[[int, int], None],
    ) -> list[PdfPage]:
        """Create printable PNG pages and thumbnails from a static HTML or HTM file."""
        source = Path(source)
        if source.suffix.lower() not in {".html", ".htm"}:
            raise ValueError("Selecione um arquivo HTML ou HTM.")

        html = self._read_html(source)
        extracted_text = self._extract_text(html)
        if not extracted_text and not re.search(r"<(img|table|svg|canvas)\b", html, re.IGNORECASE):
            raise ValueError("O HTML não possui conteúdo visual ou texto legível para importar.")

        destination.mkdir(parents=True, exist_ok=True)
        content_width = self.PAGE_WIDTH - 2 * self.MARGIN
        content_height = self.PAGE_HEIGHT - 2 * self.MARGIN

        document = QTextDocument()
        document.setBaseUrl(QUrl.fromLocalFile(str(source.parent.resolve()) + "/"))
        document.setDocumentMargin(0)
        document.setDefaultStyleSheet(
            "body { font-family: Arial, sans-serif; font-size: 11pt; color: #202124; } "
            "h1 { font-size: 22pt; } h2 { font-size: 17pt; } h3 { font-size: 14pt; } "
            "table { border-collapse: collapse; width: 100%; } "
            "th { background: #d9e2e8; font-weight: bold; } "
            "td, th { border: 1px solid #9aa7b0; padding: 5px; } "
            "img { max-width: 100%; }"
        )
        document.setHtml(html)
        document.setTextWidth(content_width)

        document_height = max(1, math.ceil(document.size().height()))
        total_pages = max(1, math.ceil(document_height / content_height))
        pages: list[PdfPage] = []

        for index in range(total_pages):
            image = QImage(self.PAGE_WIDTH, self.PAGE_HEIGHT, QImage.Format.Format_ARGB32)
            image.fill(QColor("white"))
            painter = QPainter(image)
            try:
                painter.setClipRect(QRectF(self.MARGIN, self.MARGIN, content_width, content_height))
                painter.translate(self.MARGIN, self.MARGIN - index * content_height)
                document.drawContents(painter)
            finally:
                painter.end()

            page_number = index + 1
            image_path = destination / f"html_page_{page_number:03d}.png"
            thumbnail_path = destination / f"html_thumbnail_{page_number:03d}.png"
            if not image.save(str(image_path), "PNG"):
                raise OSError(f"Não foi possível gerar a imagem da página HTML {page_number}.")
            thumbnail = image.scaled(
                self.THUMBNAIL_SIZE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            if not thumbnail.save(str(thumbnail_path), "PNG"):
                raise OSError(f"Não foi possível gerar a miniatura da página HTML {page_number}.")

            pages.append(
                PdfPage(
                    number=page_number,
                    image_path=image_path,
                    thumbnail_path=thumbnail_path,
                    extracted_text=self._text_for_page(extracted_text, index, total_pages),
                    source_type="html",
                )
            )
            on_progress(page_number, total_pages)

        return pages
