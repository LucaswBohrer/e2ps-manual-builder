"""Project export service handling R Markdown generation and asset management."""

from __future__ import annotations

import re
import shutil
import unicodedata
from datetime import date
from pathlib import Path
from typing import Callable

from manual_builder.models import ManualSection, ManualSubsection, PdfPage
from manual_builder.translation_service import TranslationService, create_translation_service
from manual_builder.image_utils import convert_image_to_png


RMD_TEMPLATE = r"""---
title: ''
Autor: E2PS
header-includes:
  - \usepackage{{fontspec}}
  - \setmainfont{{Gotham Rounded Book}}
  - \usepackage{{sectsty}}
  - \usepackage{{amsmath}}
  - \usepackage{{unicode-math}}
  - \usepackage{{longtable}}
  - \usepackage{{booktabs}}
  - \usepackage{{array}}
  - \usepackage{{enumitem}}
  - \setlist{{nosep,leftmargin=*}}
  - \renewcommand{{\arraystretch}}{{1.15}}
  - \setlength{{\tabcolsep}}{{5pt}}
  - \allsectionsfont{{\color{{orange}}}}
  - \usepackage{{fancyhdr}}
  - \pagestyle{{fancy}}
  - \fancyhead{{}}
  - \setlength{{\headheight}}{{42pt}}
  - \fancyhead[LO,RE]{{\fontsize{{8}}{{10}}\selectfont Technical Documentation by E2PS}}
  - \fancyhead[RO,LE]{{\includegraphics[width = 0.13\textwidth]{{LogoHeader.png}}}}
  - \fancyfoot{{}}
  - \renewcommand{{\headrulewidth}}{{0pt}}
  - \renewcommand{{\footrulewidth}}{{0pt}}
  - \hoffset 0cm
  - \voffset -0.7cm
  - \usepackage{{float}}
  - \usepackage{{setspace}}
  - \usepackage{{multicol}}
  - \fancyfoot[C]{{\fontsize{{7}}{{10}}\selectfont E2PS Group | Eigelstein 101 - 113 | 50668 Cologne | Germany PHONE:+49 221 8017 7819 | EMAIL trust@e2ps.com | e2ps.com \fontsize{{8}}{{10}}\selectfont \\ \thepage}}
output:
  pdf_document:
    includes: null
    latex_engine: lualatex
  html_document:
    toc: yes
    toc_float: yes
  word_document:
    toc: yes
fontsize: 10pt
---

<style type="text/css">
  body{{ font-family: Gotham Rounded Book; font-size: 10pt; }}
  h1,h2,h3 {{ color: orange; }}
  h1{{ font-size: 20pt; }}
  h2{{ font-size: 15pt; }}
  h3{{ font-size: 12pt; }}
</style>

<!--#################################################################################################################-->
<!--Capa PDF -->

\begin{{centering}}
\vspace{{2.2cm}}

```{{r uni_logo, echo=FALSE, out.width="20%"}}
knitr::include_graphics("LogoHeader.png")
```

\vspace{{1cm}}
\Large
{{\bf {manual_label}}}
\Huge
\doublespacing

{{\bf {title}}}
\vspace{{3cm}}
```{{r uni_logo2, echo=FALSE, out.width="20%"}}
knitr::include_graphics("Capa.png")
```

\vspace{{2cm}}
\normalsize
\singlespacing
\end{{centering}}

\scriptsize
\begin{{multicols}}{{2}}
\begin{{flushleft}}
{publication_date}
\end{{flushleft}}
\begin{{flushright}}
Code:{manual_code}
\end{{flushright}}
\end{{multicols}}

\normalsize
\centering
\raggedright
\newpage
\tableofcontents

{sections}
"""


class ProjectExportService:
    """Export selected pages as standard E2PS R Markdown projects."""

    _asset_directory = Path(__file__).parent / "assets"
    _manual_labels = {
        "pt": "Manual de Operação e Informações Técnicas",
        "en": "Operation Manual and Technical Information",
        "es": "Manual de Operación e Información Técnica",
    }
    _language_folders = {
        "pt": "Português",
        "en": "English",
        "es": "Español",
    }

    def export(
        self,
        destination: Path,
        title: str,
        sections: list[ManualSection],
        manual_code: str = "",
        publication_date: str | None = None,
        cover_image_path: Path | None = None,
    ) -> Path:
        """Create the original single-language Portuguese project format."""
        project_dir = destination / self._safe_name(title)
        self._write_language_project(
            project_dir,
            title,
            sections,
            manual_code,
            publication_date or date.today().strftime("%Y-%m"),
            "pt",
            cover_image_path=cover_image_path,
        )
        return project_dir

    def export_multilingual(
        self,
        destination: Path,
        title: str,
        sections: list[ManualSection],
        languages: list[str],
        source_language: str,
        translation_provider: str,
        api_key: str,
        translation_endpoint: str,
        manual_code: str,
        publication_date: str,
        on_progress: Callable[[int, int], None],
        model: str = "llama-3.3-70b-versatile",
        cover_image_path: Path | None = None,
    ) -> Path:
        """Create independent language folders and translate non-source pages with AI."""
        project_dir = destination / self._safe_name(title)
        requires_translation = any(lang != source_language for lang in languages)
        requires_structured_content = any(
            isinstance(item, PdfPage) and getattr(item, "export_mode", "image") == "text"
            for section in sections
            for item in (
                list(section.content)
                + [sub_item for subsection in section.subsections for sub_item in subsection.content]
            )
        )
        # A mesma IA também é necessária na língua de origem quando há páginas em modo
        # Texto/Tabela: ela transforma o texto extraído do PDF em Markdown técnico legível.
        translator = (
            create_translation_service(
                translation_provider,
                api_key,
                translation_endpoint,
                source_language,
                model=model,
            )
            if requires_translation or requires_structured_content
            else None
        )
        total_pages = sum(
            sum(1 for item in section.content if isinstance(item, PdfPage))
            + sum(sum(1 for sub_item in sub.content if isinstance(sub_item, PdfPage)) for sub in section.subsections)
            for section in sections
        ) * len(languages)
        completed_pages = 0

        for language in languages:
            language_title = title
            language_sections = sections
            if translator is not None and language != source_language:
                language_title = translator.translate_text(title, language)
                language_sections = []
                from dataclasses import replace
                for section in sections:
                    sec_title = translator.translate_text(section.title, language)
                    sec_content = []
                    for item in section.content:
                        if isinstance(item, PdfPage):
                            # Preservar o export_mode ao criar a estrutura traduzida
                            sec_content.append(item)
                        elif isinstance(item, str) and item.strip():
                            sec_content.append(translator.translate_text(item, language))
                    
                    subsections = []
                    for sub in section.subsections:
                        sub_title = translator.translate_text(sub.title, language)
                        sub_content = []
                        for sub_item in sub.content:
                            if isinstance(sub_item, PdfPage):
                                sub_content.append(sub_item)
                            elif isinstance(sub_item, str) and sub_item.strip():
                                sub_content.append(translator.translate_text(sub_item, language))
                        subsections.append(ManualSubsection(title=sub_title, content=sub_content))
                    language_sections.append(ManualSection(title=sec_title, content=sec_content, subsections=subsections))

            pages_in_language = sum(
                sum(1 for item in section.content if isinstance(item, PdfPage))
                + sum(sum(1 for sub_item in sub.content if isinstance(sub_item, PdfPage)) for sub in section.subsections)
                for section in sections
            )
            exported_in_language = 0

            def page_exported() -> None:
                """Report language-export progress with a stable total."""
                nonlocal exported_in_language
                exported_in_language += 1
                on_progress(completed_pages + exported_in_language, total_pages)

            self._write_language_project(
                project_dir / self._language_folders[language],
                language_title,
                language_sections,
                manual_code,
                publication_date,
                language,
                translator,
                (language != source_language or requires_structured_content)
                and translator.supports_page_translation
                if translator is not None
                else False,
                page_exported,
                cover_image_path=cover_image_path,
            )
            completed_pages += pages_in_language
        return project_dir

    def _write_language_project(
        self,
        project_dir: Path,
        title: str,
        sections: list[ManualSection],
        manual_code: str,
        publication_date: str,
        language: str,
        translator: TranslationService | None = None,
        translate_images: bool = False,
        on_page_exported: Callable[[], None] | None = None,
        cover_image_path: Path | None = None,
    ) -> None:
        """Write one standalone manual, translating its selected PNG pages when asked."""
        image_dir = project_dir / "img"
        output_dir = project_dir / "output"
        image_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(exist_ok=True)
        self._copy_standard_assets(project_dir, cover_image_path)

        section_blocks: list[str] = []
        for section_index, section in enumerate(sections, start=1):
            section_content_blocks = self._render_mixed_content(
                section.content,
                section_index,
                0,
                image_dir,
                language,
                translator,
                translate_images,
                on_page_exported,
                content_title=section.title,
            )

            subsection_blocks: list[str] = []
            for subsection_index, subsection in enumerate(section.subsections, start=1):
                sub_content_blocks = self._render_mixed_content(
                    subsection.content,
                    section_index,
                    subsection_index,
                    image_dir,
                    language,
                    translator,
                    translate_images,
                    on_page_exported,
                    content_title=f"{section.title}\n{subsection.title}",
                )
                if sub_content_blocks.strip():
                    subsection_blocks.append(f"## {subsection.title}\n\n{sub_content_blocks}")

            all_content = "\n\n".join(
                part for part in [section_content_blocks, "\n\n".join(subsection_blocks)] if part
            )
            if all_content.strip():
                # Classes tabset são úteis apenas no HTML e podem aumentar a fragmentação
                # de páginas no Pandoc/LaTeX. O PDF recebe uma hierarquia simples e estável.
                section_blocks.append(f"# {section.title}\n\n{all_content}")

        content = RMD_TEMPLATE.format(
            title=title.replace("'", "\\'"),
            sections="\n\n".join(section_blocks),
            manual_code=manual_code,
            publication_date=publication_date,
            manual_label=self._manual_labels[language],
        )
        (project_dir / "manual.rmd").write_text(content, encoding="utf-8")

    _VISUAL_SECTION_TERMS = (
        "imagem", "ilustra", "figura", "desenho", "diagrama", "vista explodida",
        "peças", "pecas", "parts", "spare",
    )
    _GRAPHIC_TEXT_MARKERS = (
        "figure ", "fig. ", "drawing", "diagram", "dimensional", "dimensions",
        "exploded view", "vista explodida", "lista de peças", "parts list",
    )

    @classmethod
    def _content_prefers_images(cls, content_title: str) -> bool:
        """Return whether a user-created section is explicitly an illustration section."""
        normalized = cls._normalized_heading(content_title)
        return any(term in normalized for term in cls._VISUAL_SECTION_TERMS)

    @classmethod
    def _source_looks_graphical(cls, page: PdfPage, content_title: str) -> bool:
        """Identify clear diagrams locally without spending vision calls on text pages."""
        if getattr(page, "export_mode", "image") == "image":
            return True
        if cls._content_prefers_images(content_title):
            return True
        text = page.extracted_text or ""
        normalized = text.lower()
        if not normalized.strip():
            return False
        has_graphic_marker = any(marker in normalized for marker in cls._GRAPHIC_TEXT_MARKERS)
        # Desenhos de conjunto podem ter muito texto extraível (cotas, códigos e tabelas),
        # portanto o tamanho do texto não é critério suficiente para classificá-los.
        drawing_codes = len(re.findall(r"\b[A-Z]{1,5}[ -]?\d{4,}\b", text))
        dimensions = len(
            re.findall(
                r"(?:\b\d+(?:[.,]\d+)?\s*(?:mm|cm|m|in|°)|\(\s*\d+(?:[.,]\d+)?\s*\))",
                normalized,
            )
        )
        figures = len(re.findall(r"\b(?:figure|figura|fig\.)\s*\d+", normalized))
        drawing_dense = drawing_codes >= 3 or dimensions >= 4 or figures >= 2
        dimension_heavy = "ø" in normalized or "diameter" in normalized or "dimens" in normalized
        return has_graphic_marker and (drawing_dense or dimension_heavy or len(normalized) < 700)

    @staticmethod
    def _image_rmd_block(
        section_index: int,
        subsection_index: int,
        page_counter: int,
        filename: str,
    ) -> str:
        """Return a stable R Markdown image block for an intentionally visual page."""
        return (
            "```{r section_%03d_subsection_%03d_page_%03d, echo=FALSE, "
            "fig.align='center', out.width='94%%', fig.pos='H'}\n"
            "knitr::include_graphics('img/%s')\n```"
            % (section_index, subsection_index, page_counter, filename)
        )

    @staticmethod
    def _contains_ai_internal_artifact(value: str) -> bool:
        """Identify content that is a model instruction or image description, not manual text."""
        return bool(
            re.search(
                r"(?is)\b(?:the\s+user\s+(?:wants|needs|is\s+asking)|"
                r"i\s+(?:need|should)\s+to\s+(?:transcribe|translate|describe)|"
                r"the\s+image\s+(?:appears|shows|contains)|"
                r"need\s+to\s+accurately\s+(?:transcribe|translate)|"
                r"technical\s+manual\s+(?:page|image)\s+(?:appears|shows))\b",
                value or "",
            )
        )

    @classmethod
    def _safe_export_source_text(cls, value: str) -> str:
        """Return source text only when it is safe for final publication.

        Older saved projects may contain visual-analysis text in ``extracted_text``. A single
        unclosed reasoning tag or prompt-like sentence means that page must be re-read visually
        or flagged for manual review; it must never be emitted as R Markdown prose.
        """
        raw = value or ""
        if re.search(r"<think(?:\s[^>]*)?>", raw, flags=re.IGNORECASE) and not re.search(
            r"</think>", raw, flags=re.IGNORECASE
        ):
            return ""
        cleaned = cls._strip_ai_metacommentary(raw)
        if not cleaned or cls._contains_ai_internal_artifact(cleaned):
            return ""
        return cleaned

    def _render_textual_page_batch(
        self,
        pages: list[PdfPage],
        language: str,
        translator: TranslationService | None,
        content_title: str,
        on_page_exported: Callable[[], None] | None,
    ) -> str:
        """Render contiguous textual PDF pages from their extracted source text.

        A section is translated once as an ordered source block. In the source language,
        formatting is fully local and deterministic, with no request to the provider.
        """
        source_text = "\n\n".join(
            self._safe_export_source_text(page.extracted_text)
            for page in pages
            if self._safe_export_source_text(page.extracted_text)
        ).strip()
        structured_text = source_text
        translate_batch = getattr(translator, "translate_section_text", None) if translator else None
        if source_text and callable(translate_batch):
            try:
                translated = translate_batch(source_text, language)
                if translated and translated.strip():
                    structured_text = translated
            except Exception:
                structured_text = source_text
        elif source_text and translator is not None:
            # Compatibility path for custom/older providers: one batch request, never one per page.
            try:
                translated = translator.extract_structured_content(
                    pages[0].image_path, language, source_text
                )
                if translated and translated.strip() and translated.strip() != "[[KEEP_AS_IMAGE]]":
                    structured_text = translated
            except Exception:
                structured_text = source_text

        rendered = self._format_rmd_text(structured_text, context_title=content_title)
        if not rendered:
            page_numbers = ", ".join(str(page.number) for page in pages)
            rendered = (
                "<!-- Conteúdo textual indisponível para as páginas "
                f"{page_numbers}; revise a seleção no editor. -->"
            )
        if on_page_exported is not None:
            for _page in pages:
                on_page_exported()
        return rendered

    def _render_scanned_page(
        self,
        page: PdfPage,
        language: str,
        translator: TranslationService | None,
        content_title: str,
    ) -> str:
        """Use vision only for a page without selectable source text."""
        structured_text = ""
        if translator is not None:
            try:
                structured_text = translator.extract_structured_content(page.image_path, language, "")
            except Exception:
                structured_text = ""
        structured_text = self._safe_export_source_text(structured_text)
        if structured_text.strip() and structured_text.strip() != "[[KEEP_AS_IMAGE]]":
            return self._format_rmd_text(structured_text, context_title=content_title)
        if structured_text.strip() == "[[KEEP_AS_IMAGE]]":
            return "[[KEEP_AS_IMAGE]]"
        return (
            "<!-- Não foi possível ler automaticamente o conteúdo da página "
            f"{page.number}. Adicione um recorte ou texto manualmente no editor. -->"
        )

    def _render_mixed_content(
        self,
        content_items: list[PdfPage | str],
        section_index: int,
        subsection_index: int,
        image_dir: Path,
        language: str,
        translator: TranslationService | None,
        translate_images: bool,
        on_page_exported: Callable[[], None] | None,
        content_title: str = "",
    ) -> str:
        """Render content in order, batching only contiguous textual PDF pages."""
        rendered_blocks: list[str] = []
        pending_text_pages: list[PdfPage] = []
        page_counter = 0

        def flush_text_pages() -> None:
            nonlocal pending_text_pages
            if pending_text_pages:
                rendered_blocks.append(
                    self._render_textual_page_batch(
                        pending_text_pages, language, translator, content_title, on_page_exported
                    )
                )
                pending_text_pages = []

        for item in content_items:
            if isinstance(item, str):
                flush_text_pages()
                if item.strip():
                    rendered_blocks.append(self._format_rmd_text(item, context_title=content_title))
                continue
            if not isinstance(item, PdfPage):
                continue

            page_counter += 1
            safe_source_text = self._safe_export_source_text(item.extracted_text)
            # Conteúdo contaminado de projeto antigo não pode acionar uma rota de imagem
            # só porque contém palavras como "figure" ou "drawing" dentro do prompt.
            contaminated_source = bool(item.extracted_text.strip()) and not safe_source_text
            graphical = (not contaminated_source) and self._source_looks_graphical(item, content_title)
            if not graphical and safe_source_text:
                # A limpeza é gravada na cópia usada para o lote, preservando o objeto
                # original da interface e garantindo que somente fonte verificável siga
                # para a tradução por seção.
                from dataclasses import replace
                pending_text_pages.append(replace(item, extracted_text=safe_source_text))
                continue

            flush_text_pages()
            scanned_or_visual = self._render_scanned_page(item, language, translator, content_title)
            if scanned_or_visual != "[[KEEP_AS_IMAGE]]" and not graphical:
                rendered_blocks.append(scanned_or_visual)
                if on_page_exported is not None:
                    on_page_exported()
                continue

            # Only confirmed illustrations, explicitly selected image pages and visual sections
            # are copied into the final project. Textual pages never fall back to the source image.
            target = image_dir / item.filename
            shutil.copy2(item.image_path, target)
            if translate_images and translator is not None and getattr(item, "export_mode", "image") == "image":
                translator.translate_page(item.image_path, target, language)
            rendered_blocks.append(
                self._image_rmd_block(section_index, subsection_index, page_counter, item.filename)
            )
            if on_page_exported is not None:
                on_page_exported()

        flush_text_pages()
        return "\n\n".join(block for block in rendered_blocks if block.strip())

    @staticmethod
    def _strip_ai_metacommentary(value: str) -> str:
        """Remove AI explanations and source/translation wrappers from exportable text.

        This is intentionally a second safety layer after the translation service: text blocks
        may also come from an older saved project or be pasted directly by the user.
        """
        cleaned = re.sub(
            r"<think(?:\s[^>]*)?>.*?</think>",
            "",
            value or "",
            flags=re.IGNORECASE | re.DOTALL,
        ).strip()
        incomplete_reasoning = re.search(r"<think(?:\s[^>]*)?>", cleaned, flags=re.IGNORECASE)
        if incomplete_reasoning:
            cleaned = cleaned[:incomplete_reasoning.start()].strip()
        result_markers = list(
            re.finditer(
                r"(?im)^\s*(?:tradu[cç][aã]o|translation|conte[úu]do\s+traduzido|resultado\s+final)\s*:\s*",
                cleaned,
            )
        )
        if result_markers:
            final_block = cleaned[result_markers[-1].end():].strip()
            if final_block:
                cleaned = final_block

        blocked_line = re.compile(
            r"(?i)^\s*(?:"
            r"n[aã]o\s+h[aá]\s+necessidade\s+de\s+tradu[cç][aã]o|"
            r"o\s+texto\s+j[aá]\s+est[aá]|"
            r"(?:aqui\s+est[aá]|segue)\s+(?:a\s+)?tradu[cç][aã]o|"
            r"(?:texto|text|texto\s+original|original|source)\s*:|"
            r"(?:tradu[cç][aã]o|translation|conte[úu]do\s+traduzido|resultado\s+final)\s*:"
            r")"
        )
        cleaned = "\n".join(
            line.rstrip() for line in cleaned.splitlines() if not blocked_line.match(line)
        ).strip()
        return "" if ProjectExportService._contains_ai_internal_artifact(cleaned) else cleaned

    @staticmethod
    def _normalized_heading(value: str) -> str:
        """Create a comparison key for document headings without numbering or accents."""
        no_accents = "".join(
            character
            for character in unicodedata.normalize("NFD", value or "")
            if unicodedata.category(character) != "Mn"
        )
        no_numbering = re.sub(r"^\s*\d+(?:\.\d+)*\.?\s*", "", no_accents)
        return re.sub(r"[^a-z0-9]+", " ", no_numbering.lower()).strip()

    @staticmethod
    def _is_contact_fragment_heading(value: str) -> bool:
        """Identify footer/contact fragments that must never become TOC entries."""
        normalized = ProjectExportService._normalized_heading(value)
        return normalized in {
            "como",
            "como contatar",
            "contatar",
            "contatar alfa",
            "alfa",
            "alfa laval",
            "alfa laval ab",
            "contact",
            "contact alfa laval",
        }

    @classmethod
    def _remove_duplicate_source_headings(cls, text: str, context_title: str) -> str:
        """Keep source chapter labels from becoming duplicate E2PS top-level sections."""
        context_labels = [
            label.strip()
            for label in re.split(r"[\n|]+", context_title or "")
            if label.strip()
        ]
        contexts = {cls._normalized_heading(label) for label in context_labels}
        contexts.discard("")
        repeated_context_with_body = [
            re.compile(
                rf"^(?:#{1,6}\s*)?\d+(?:\.\d+)*\.?\s*{re.escape(label)}\s+(?P<body>.+)$",
                flags=re.IGNORECASE,
            )
            for label in context_labels
        ]
        result: list[str] = []
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if re.fullmatch(r"\d+(?:\.\d+)*\.?", line):
                continue

            # Alguns extratores unem o cabeçalho visual da página ao primeiro
            # parágrafo (por exemplo: "2 Segurança Práticas inseguras...").
            # Removemos só o cabeçalho duplicado e preservamos a instrução real.
            body_match = next(
                (pattern.match(line) for pattern in repeated_context_with_body if pattern.match(line)),
                None,
            )
            if body_match:
                body = (body_match.groupdict().get("body") or "").strip()
                if body:
                    result.append(body)
                    continue

            match = re.match(r"^(#{1,6})\s*(.*?)\s*$", line)
            candidate = match.group(2) if match else line
            candidate = re.sub(r"^\d+(?:\.\d+)*\.?\s*", "", candidate).strip()
            normalized = cls._normalized_heading(candidate)
            is_context_heading = bool(normalized and normalized in contexts)
            if is_context_heading:
                continue

            if match:
                if not candidate or cls._is_contact_fragment_heading(candidate):
                    continue
                # The E2PS section itself uses H1. Source headings always start at H2
                # so the table of contents stays clean and manufacturer chapter numbers
                # do not create a second top-level hierarchy.
                depth = min(max(len(match.group(1)) + 1, 2), 4)
                result.extend(["", f"{'#' * depth} {candidate}", ""])
            else:
                result.append(raw_line.rstrip())
        return "\n".join(result)

    @staticmethod
    def _expand_inline_markdown_tables(text: str) -> str:
        """Recover tables flattened by OCR/vision into a single line of pipe tokens."""
        repaired: list[str] = []
        for raw_line in text.splitlines():
            first_pipe = raw_line.find("|")
            if first_pipe < 0 or raw_line.count("|") < 6:
                repaired.append(raw_line.rstrip())
                continue

            prefix = raw_line[:first_pipe].strip()
            cells = [cell.strip() for cell in raw_line[first_pipe:].split("|") if cell.strip()]
            column_count = 0
            for candidate_count in range(2, min(6, len(cells) // 2) + 1):
                separators = cells[candidate_count : candidate_count * 2]
                if len(separators) == candidate_count and all(
                    re.fullmatch(r":?-{2,}:?", cell) for cell in separators
                ):
                    column_count = candidate_count
                    break
            if not column_count:
                repaired.append(raw_line.rstrip())
                continue

            if prefix:
                repaired.extend([prefix, ""])
            header = cells[:column_count]
            repaired.append("| " + " | ".join(header) + " |")
            repaired.append("| " + " | ".join("---" for _ in header) + " |")
            data_cells = cells[column_count * 2 :]
            for offset in range(0, len(data_cells), column_count):
                row = data_cells[offset : offset + column_count]
                if len(row) == column_count:
                    repaired.append("| " + " | ".join(row) + " |")
            repaired.append("")
        return "\n".join(repaired)

    @staticmethod
    def _collapse_overlapping_pdf_lines(text: str) -> str:
        """Repair word-by-word overlap artifacts produced by some selectable PDFs.

        Certain manufacturer PDFs expose the same sentence through overlapping text boxes.
        PyMuPDF then yields a sequence such as ``Always / Always read / read / read the``.
        This routine joins only short, consecutively overlapping fragments and leaves normal
        paragraphs, Markdown and tables untouched.
        """
        def clean_inline_artifacts(line: str) -> str:
            # ``isis`` and ``thethe`` commonly arise where two text boxes overlap exactly.
            cleaned = re.sub(r"\b([A-Za-zÀ-ÿ]{2,})\1\b", r"\1", line)
            # A second extractor artifact is a duplicated word inside an otherwise normal line.
            return re.sub(r"\b([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9_-]*)(?:\s+\1\b)+", r"\1", cleaned)

        source_lines = [clean_inline_artifacts(line) for line in text.splitlines()]
        deduplicated: list[str] = []
        for line in source_lines:
            if deduplicated and line.strip() and line.strip().casefold() == deduplicated[-1].strip().casefold():
                continue
            deduplicated.append(line)

        def can_merge(line: str) -> bool:
            words = line.strip().split()
            # Linhas técnicas completas podem ter 25–35 palavras. Ainda assim, uma
            # sobreposição literal no final/início é segura de recompor e evita o
            # "for for" observado no manual LKH. Tabelas, listas e títulos continuam
            # fora desse tratamento.
            return bool(words) and len(words) <= 48 and not line.lstrip().startswith(("#", "|", "- ", "* "))

        repaired: list[str] = []
        for line in deduplicated:
            if not repaired or not can_merge(line) or not can_merge(repaired[-1]):
                repaired.append(line.rstrip())
                continue
            previous_words = repaired[-1].strip().split()
            current_words = line.strip().split()
            overlap = 0
            for size in range(min(len(previous_words), len(current_words), 4), 0, -1):
                if [word.casefold() for word in previous_words[-size:]] == [
                    word.casefold() for word in current_words[:size]
                ]:
                    overlap = size
                    break
            if overlap:
                repaired[-1] = " ".join(previous_words + current_words[overlap:])
            else:
                repaired.append(line.rstrip())
        return "\n".join(repaired)

    @staticmethod
    def _format_rmd_text(value: str, context_title: str = "") -> str:
        """Normalize human/AI text into safe, readable R Markdown.

        Existing Markdown tables and ordered lists are preserved. Plain bullet markers are
        normalized, and short consecutive ``rótulo: valor`` lines become a table so technical
        data remains legible after knitting to PDF.
        """
        text = ProjectExportService._strip_ai_metacommentary(value)
        text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        text = ProjectExportService._collapse_overlapping_pdf_lines(text)
        text = re.sub(r"^```(?:markdown|md)?\s*|\s*```$", "", text, flags=re.IGNORECASE).strip()
        text = ProjectExportService._expand_inline_markdown_tables(text)
        text = ProjectExportService._remove_duplicate_source_headings(text, context_title)
        if not text:
            return ""

        lines = [line.rstrip() for line in text.split("\n")]
        normalized: list[str] = []
        index = 0
        while index < len(lines):
            line = lines[index].strip()
            if not line:
                normalized.append("")
                index += 1
                continue

            # Convert a short run of technical label/value pairs into a Pandoc table.
            pair_rows: list[tuple[str, str]] = []
            cursor = index
            while cursor < len(lines):
                candidate = lines[cursor].strip()
                if (
                    not candidate
                    or candidate.startswith(("#", "- ", "* ", "+ ", "|"))
                    or re.match(r"^\d+[.)]\s+", candidate)
                    or candidate.count(":") != 1
                ):
                    break
                label, description = (part.strip() for part in candidate.split(":", 1))
                if not label or not description or len(label) > 48:
                    break
                pair_rows.append((label, description))
                cursor += 1
            if len(pair_rows) >= 2:
                normalized.extend(["| Item | Descrição |", "|:--|:--|"])
                for label, description in pair_rows:
                    safe_label = label.replace("|", r"\|")
                    safe_description = description.replace("|", r"\|")
                    normalized.append(f"| {safe_label} | {safe_description} |")
                normalized.append("")
                index = cursor
                continue

            if re.match(r"^#{2,6}\s+", line):
                if normalized and normalized[-1]:
                    normalized.append("")
                normalized.append(line)
                if index + 1 < len(lines) and lines[index + 1].strip():
                    normalized.append("")
                index += 1
                continue

            line = re.sub(r"^[•‣▪◦]\s*", "- ", line)
            line = re.sub(r"^\*\s+", "- ", line)
            line = re.sub(r"^(\d+)\)\s+", r"\1. ", line)
            normalized.append(line)
            index += 1

        # Remove repeated blank lines that create oversized gaps in the final PDF.
        rendered = "\n".join(normalized)
        rendered = re.sub(r"\n{3,}", "\n\n", rendered)
        return rendered.strip()

    def _copy_standard_assets(self, project_dir: Path, cover_image_path: Path | None = None) -> None:
        """Copy standard assets and normalize any custom cover to a valid PNG."""
        has_custom_cover = cover_image_path is not None and cover_image_path.is_file()
        for asset in self._asset_directory.iterdir():
            if asset.is_file():
                if asset.name.lower() == "capa.png" and has_custom_cover:
                    continue
                shutil.copy2(asset, project_dir / asset.name)

        if has_custom_cover:
            convert_image_to_png(cover_image_path, project_dir / "Capa.png")

    @staticmethod
    def _safe_name(value: str) -> str:
        """Convert a title into a safe Windows directory name."""
        invalid = '<>:"/\\|?*'
        clean = "".join("_" if character in invalid else character for character in value)
        return clean.strip(" .") or "Projeto_E2PS"
