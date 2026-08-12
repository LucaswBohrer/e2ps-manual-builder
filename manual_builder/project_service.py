"""Project export service handling R Markdown generation and asset management."""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path
from typing import Callable

from manual_builder.models import ManualSection, ManualSubsection
from manual_builder.translation_service import (
    TranslationService,
    create_translation_service,
)


RMD_TEMPLATE = r"""---
title: ''
Autor: E2PS
header-includes:
  - \usepackage{{fontspec}}
  - \setmainfont{{Gotham Rounded Book.otf}}[Path=./]
  - \usepackage{{sectsty}}
  - \usepackage{{amsmath}}
  - \usepackage{{unicode-math}}
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

```{{r, include=FALSE}}
library(rsvg)
library(magick)
```

\newpage

<!--#################################################################################################################-->
<!--Capa PDF -->

\begin{{centering}}
\vspace{{4cm}}

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
        cover_image_path: Path | None = None,
    ) -> Path:
        """Create independent language folders and translate non-source pages with AI."""
        project_dir = destination / self._safe_name(title)
        requires_translation = any(lang != source_language for lang in languages)
        translator = (
            create_translation_service(
                translation_provider,
                api_key,
                translation_endpoint,
                source_language,
            )
            if requires_translation
            else None
        )
        total_pages = sum(
            len(section.pages)
            + sum(len(subsection.pages) for subsection in section.subsections)
            for section in sections
        ) * len(languages)
        completed_pages = 0

        for language in languages:
            language_title = title
            language_sections = sections
            if translator is not None and language != source_language:
                language_title = translator.translate_text(title, language)
                language_sections = [
                    ManualSection(
                        title=translator.translate_text(section.title, language),
                        pages=section.pages,
                        subsections=[
                            ManualSubsection(
                                title=translator.translate_text(subsection.title, language),
                                pages=subsection.pages,
                            )
                            for subsection in section.subsections
                        ],
                    )
                    for section in sections
                ]

            pages_in_language = sum(
                len(section.pages)
                + sum(len(subsection.pages) for subsection in section.subsections)
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
                language != source_language and translator.supports_page_translation
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
            section_content = self._page_blocks(
                section.pages,
                section_index,
                0,
                image_dir,
                language,
                translator,
                translate_images,
                on_page_exported,
            )
            subsection_blocks: list[str] = []
            for subsection_index, subsection in enumerate(section.subsections, start=1):
                subsection_pages = self._page_blocks(
                    subsection.pages,
                    section_index,
                    subsection_index,
                    image_dir,
                    language,
                    translator,
                    translate_images,
                    on_page_exported,
                )
                subsection_blocks.append(f"## {subsection.title}\n\n{subsection_pages}")
            all_content = "\n\n".join(
                part for part in [section_content, "\n\n".join(subsection_blocks)] if part
            )
            section_blocks.append(f"# {section.title} {{.tabset .tabset-fade}}\n\n{all_content}")

        content = RMD_TEMPLATE.format(
            title=title.replace("'", "\\'"),
            sections="\n\n".join(section_blocks),
            manual_code=manual_code,
            publication_date=publication_date,
            manual_label=self._manual_labels[language],
        )
        (project_dir / "manual.rmd").write_text(content, encoding="utf-8")

    def _page_blocks(
        self,
        pages: list,
        section_index: int,
        subsection_index: int,
        image_dir: Path,
        language: str,
        translator: TranslationService | None,
        translate_images: bool,
        on_page_exported: Callable[[], None] | None,
    ) -> str:
        """Export a list of page variants and return their R Markdown chunks."""
        image_blocks: list[str] = []
        for page_index, page in enumerate(pages, start=1):
            target = image_dir / page.filename
            if translate_images and translator is not None:
                translator.translate_page(page.image_path, target, language)
            else:
                shutil.copy2(page.image_path, target)
            if on_page_exported is not None:
                on_page_exported()
            image_blocks.append(
                "```{r section_%03d_subsection_%03d_page_%03d, echo=FALSE, "
                "fig.align='center', out.width='100%%'}\n"
                "knitr::include_graphics('img/%s')\n```"
                % (section_index, subsection_index, page_index, page.filename)
            )
        return "\n\n".join(image_blocks)

    def _copy_standard_assets(self, project_dir: Path, cover_image_path: Path | None = None) -> None:
        """Copy logo, typography and cover image shipped with the E2PS standard package."""
        for asset in self._asset_directory.iterdir():
            if asset.is_file():
                if asset.name.lower() == "capa.png" and cover_image_path is not None and cover_image_path.is_file():
                    continue  # Will copy custom cover below
                shutil.copy2(asset, project_dir / asset.name)
        
        if cover_image_path is not None and cover_image_path.is_file():
            shutil.copy2(cover_image_path, project_dir / "Capa.png")

    @staticmethod
    def _safe_name(value: str) -> str:
        """Convert a title into a safe Windows directory name."""
        invalid = '<>:"/\\|?*'
        clean = "".join("_" if character in invalid else character for character in value)
        return clean.strip(" .") or "Projeto_E2PS"
