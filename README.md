# E2PS Manual Builder

Desktop application for creating the initial structure of E2PS technical manuals from PDF files. It provides an efficient first step for manual production: select PDF pages, export them as PNG, and generate a ready-to-edit R Markdown project.

## Features

- Opens PDF documents and renders every page as a thumbnail.
- Allows individual page selection with checkboxes.
- Provides Select All and Deselect All controls for bulk page selection.
- Groups checked pages into user-named manual sections before export.
- Shows the selected page in a large preview.
- Exports selected pages as PNG files.
- Creates `Project/img`, `Project/output`, and `Project/manual.rmd`.
- Copies the E2PS logo and Gotham Rounded font to every exported project.
- Reproduces the E2PS PDF cover, header, footer, table of contents, and page layout.
- Inserts all exported images into `manual.rmd` using valid `knitr::include_graphics()` chunks.
- Exports technical page images at 200 DPI, separately from lightweight UI thumbnails.
- Uses a modern dark PySide6 interface with progress feedback.

## Project structure

```text
E2PS-Manual-Builder/
├── main.py
├── requirements.txt
└── manual_builder/
    ├── main_window.py       # UI orchestration
    ├── models.py            # Typed data structures
    ├── pdf_service.py       # PDF rendering
    ├── project_service.py   # R Markdown project generation
    ├── styles.py            # Central dark theme
    └── workers.py           # Background rendering thread
```

## Requirements

- Python 3.10 or newer
- A working R + Pandoc environment is only necessary when rendering the generated `.rmd` to PDF.

## Installation and usage

```powershell
cd E2PS-Manual-Builder
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

1. Select **Open PDF**.
2. Review pages in the left panel and uncheck any pages not needed.
3. Check the pages for a section, enter its name, and select **Create Section from
   Checked Pages**. Repeat for every section. Pages may be moved by checking them
   again and adding them to another section.
4. Set the manual title, code, year, and semester in the top bar, then select
   **Export Project**. The date is written as `AAAA-01` or `AAAA-02`.

The generated `manual.rmd` contains the E2PS visual baseline (cover, header, logo,
typography, and table of contents), but deliberately does not impose sections. Add
the headings appropriate to the specific equipment before or between the page images.
The cover includes a standard empty space for the equipment image. To add it manually,
copy the image to the project root and replace the placeholder box with the commented
`\\includegraphics` instruction in `manual.rmd`.

## Architecture and future AI integration

The UI, PDF rendering, project exporting, data models, and theme are separated into focused modules. Future AI functionality can be added as a service without changing UI or export logic, for example an `ai_service.py` that analyzes `PdfPage` images and returns suggested chapters and text for the R Markdown template.

## Notes

PDF page conversion is performed locally with PyMuPDF; no document data is sent to an external service.
