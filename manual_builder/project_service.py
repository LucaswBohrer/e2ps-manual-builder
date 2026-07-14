"""Creation of the standard E2PS R Markdown project structure."""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

from manual_builder.models import ManualSection


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

<!-- E2PS typography for HTML output. -->
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

\begin{{centering}}
\vspace{{4cm}}

```{{r uni_logo, echo=FALSE, out.width="20%"}}
knitr::include_graphics("LogoHeader.png")
```

\vspace{{1cm}}
\Large
{{\bf Manual de Operação e Informações Técnicas}}
\Huge
\doublespacing

{{\bf {title}}}

% Equipment cover image placeholder. To add it manually, use:
% \includegraphics[width=0.20\textwidth]{{Capa.png}}
\vspace{{3cm}}

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
\newpage

{sections}
"""


class ProjectExportService:
    """Export selected pages using the reusable E2PS project baseline."""

    _asset_directory = Path(__file__).parent / "assets"

    def export(
        self,
        destination: Path,
        title: str,
        sections: list[ManualSection],
        manual_code: str = "",
        publication_date: str | None = None,
    ) -> Path:
        """Create an E2PS project, its standard assets, and its R Markdown file."""
        project_dir = destination / self._safe_name(title)
        image_dir = project_dir / "img"
        output_dir = project_dir / "output"
        image_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(exist_ok=True)
        self._copy_standard_assets(project_dir)

        section_blocks: list[str] = []
        for section_index, section in enumerate(sections, start=1):
            image_blocks: list[str] = []
            for page in section.pages:
                target = image_dir / page.filename
                shutil.copy2(page.image_path, target)
                image_blocks.append(
                    "```{r section_%03d_page_%03d, echo=FALSE, "
                    "fig.align='center', out.width='100%%'}\n"
                    "knitr::include_graphics('img/%s')\n```"
                    % (section_index, page.number, page.filename)
                )
            section_blocks.append(
                "# %s {.tabset .tabset-fade}\n\n%s"
                % (section.title, "\n\n".join(image_blocks))
            )

        content = RMD_TEMPLATE.format(
            title=title.replace("'", "\\'"),
            sections="\n\n".join(section_blocks),
            manual_code=manual_code,
            publication_date=publication_date or date.today().strftime("%Y-%m"),
        )
        (project_dir / "manual.rmd").write_text(content, encoding="utf-8")
        return project_dir

    def _copy_standard_assets(self, project_dir: Path) -> None:
        """Copy logo and typography shipped with the E2PS standard package."""
        for asset in self._asset_directory.iterdir():
            if asset.is_file():
                shutil.copy2(asset, project_dir / asset.name)

    @staticmethod
    def _safe_name(value: str) -> str:
        """Convert a title into a safe Windows directory name."""
        invalid = '<>:"/\\|?*'
        clean = "".join("_" if character in invalid else character for character in value)
        return clean.strip(" .") or "Projeto_E2PS"
