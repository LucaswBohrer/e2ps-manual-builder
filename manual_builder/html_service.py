from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QRectF, QSize, Qt, QUrl
from PySide6.QtGui import QColor, QImage, QPainter, QTextDocument

from manual_builder.models import PdfPage


@dataclass(slots=True)
class HtmlImageHint:
    """An image found in the HTML source that may require a manual capture/crop."""

    description: str
    source: str = ""

    @property
    def message(self) -> str:
        source_note = f" ({self.source})" if self.source else ""
        return (
            f"Imagem encontrada: {self.description}{source_note}. "
            "Abra a pré-visualização HTML, crie um recorte/captura se ela for necessária "
            "no manual final e insira-o na seção correspondente."
        )


@dataclass(slots=True)
class HtmlOutlineSubsection:
    """A subsection inferred from a semantic HTML heading."""

    title: str
    content: list[str] = field(default_factory=list)
    image_hints: list[HtmlImageHint] = field(default_factory=list)


@dataclass(slots=True)
class HtmlOutlineSection:
    """A top-level section inferred from a semantic HTML heading."""

    title: str
    content: list[str] = field(default_factory=list)
    subsections: list[HtmlOutlineSubsection] = field(default_factory=list)
    image_hints: list[HtmlImageHint] = field(default_factory=list)


@dataclass(slots=True)
class HtmlStructurePlan:
    """The editable manual structure discovered directly from an HTML document."""

    document_title: str = ""
    sections: list[HtmlOutlineSection] = field(default_factory=list)
    image_count: int = 0


@dataclass(slots=True)
class _HtmlEvent:
    """Ordered semantic event extracted from the document source."""

    kind: str
    text: str = ""
    level: int = 0
    image: HtmlImageHint | None = None


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


class _HtmlSemanticExtractor(HTMLParser):
    """Extract headings, readable text and image references while retaining document order."""

    _IGNORED_TAGS = {"script", "style", "noscript", "template", "svg"}
    _BLOCK_TAGS = {
        "address", "article", "aside", "blockquote", "br", "caption", "dd", "div", "dt",
        "figcaption", "footer", "header", "li", "main", "p", "section", "table", "td", "th", "tr",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._ignored_depth = 0
        self._events: list[_HtmlEvent] = []
        self._text_buffer: list[str] = []
        self._heading_level: int | None = None
        self._heading_buffer: list[str] = []

    @staticmethod
    def _normalized(parts: list[str]) -> str:
        return re.sub(r"\s+", " ", "".join(parts)).strip()

    def _flush_text(self) -> None:
        text = self._normalized(self._text_buffer)
        self._text_buffer.clear()
        if text:
            self._events.append(_HtmlEvent(kind="text", text=text))

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized = tag.lower()
        if normalized in self._IGNORED_TAGS:
            self._ignored_depth += 1
            return
        if self._ignored_depth:
            return

        if re.fullmatch(r"h[1-6]", normalized):
            self._flush_text()
            self._heading_level = int(normalized[1])
            self._heading_buffer.clear()
            return

        if normalized == "img":
            self._flush_text()
            attributes = {name.lower(): (value or "") for name, value in attrs}
            source = attributes.get("src", "").strip()
            description = (
                attributes.get("alt", "").strip()
                or attributes.get("title", "").strip()
                or Path(source).name
                or "imagem sem descrição"
            )
            self._events.append(
                _HtmlEvent(
                    kind="image",
                    image=HtmlImageHint(description=description, source=source),
                )
            )
            return

        if normalized in self._BLOCK_TAGS:
            self._text_buffer.append("\n")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()
        if normalized in self._IGNORED_TAGS and self._ignored_depth:
            self._ignored_depth -= 1
            return
        if self._ignored_depth:
            return

        if self._heading_level is not None and normalized == f"h{self._heading_level}":
            title = self._normalized(self._heading_buffer)
            self._heading_buffer.clear()
            if title:
                self._events.append(_HtmlEvent(kind="heading", text=title, level=self._heading_level))
            self._heading_level = None
            return

        if normalized in self._BLOCK_TAGS:
            self._text_buffer.append("\n")

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        if self._heading_level is not None:
            self._heading_buffer.append(data)
        else:
            self._text_buffer.append(data)

    def events(self) -> list[_HtmlEvent]:
        self._flush_text()
        return self._events


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
    def analyze_structure(cls, source: Path) -> HtmlStructurePlan:
        """Build an editable manual outline directly from semantic HTML source.

        The document's heading hierarchy is more reliable than an LLM guess for HTML manuals.
        `h1` is treated as the manual title when it occurs only once and `h2` headings exist;
        otherwise the highest repeated heading level creates top-level manual sections.
        """
        html = cls._read_html(Path(source))
        parser = _HtmlSemanticExtractor()
        parser.feed(html)
        parser.close()
        events = parser.events()
        headings = [event for event in events if event.kind == "heading"]
        image_count = sum(1 for event in events if event.kind == "image")

        if not headings:
            default_section = HtmlOutlineSection(title="Conteúdo importado do HTML")
            for event in events:
                if event.kind == "text" and event.text:
                    default_section.content.append(event.text)
                elif event.kind == "image" and event.image is not None:
                    default_section.image_hints.append(event.image)
            return HtmlStructurePlan(sections=[default_section], image_count=image_count)

        levels = [event.level for event in headings]
        first_level = min(levels)
        first_level_count = levels.count(first_level)
        next_level_exists = any(level == first_level + 1 for level in levels)
        document_title = ""
        section_level = first_level
        if first_level_count == 1 and next_level_exists:
            first_heading = next(event for event in headings if event.level == first_level)
            document_title = first_heading.text
            section_level = first_level + 1

        plan = HtmlStructurePlan(document_title=document_title, image_count=image_count)
        current_section: HtmlOutlineSection | None = None
        current_subsection: HtmlOutlineSubsection | None = None

        def ensure_section() -> HtmlOutlineSection:
            nonlocal current_section
            if current_section is None:
                current_section = HtmlOutlineSection(title="Conteúdo geral")
                plan.sections.append(current_section)
            return current_section

        for event in events:
            if event.kind == "heading":
                if event.level < section_level:
                    if not plan.document_title:
                        plan.document_title = event.text
                    continue
                if event.level == section_level:
                    current_section = HtmlOutlineSection(title=event.text)
                    plan.sections.append(current_section)
                    current_subsection = None
                elif event.level == section_level + 1:
                    section = ensure_section()
                    current_subsection = HtmlOutlineSubsection(title=event.text)
                    section.subsections.append(current_subsection)
                else:
                    target = current_subsection if current_subsection is not None else ensure_section()
                    target.content.append(f"**{event.text}**")
                continue

            target = current_subsection if current_subsection is not None else ensure_section()
            if event.kind == "text" and event.text:
                target.content.append(event.text)
            elif event.kind == "image" and event.image is not None:
                target.image_hints.append(event.image)

        plan.sections = [
            section
            for section in plan.sections
            if section.title.strip() or section.content or section.subsections or section.image_hints
        ]
        if not plan.sections:
            plan.sections.append(HtmlOutlineSection(title="Conteúdo importado do HTML"))
        return plan

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
