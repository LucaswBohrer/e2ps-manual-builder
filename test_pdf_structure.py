"""Tests for compact, editable PDF structuring and readable R Markdown formatting."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from manual_builder.ai_service import (
    ManualAIService,
    PdfStructurePlan,
    PdfStructureSection,
    PdfStructureSubsection,
)
from manual_builder.main_window import MainWindow
from manual_builder.models import ManualSection, PdfPage
from manual_builder.project_service import ProjectExportService
from manual_builder.translation_service import ManusTranslationService, TranslationError
from manual_builder.workers import PdfStructureWorker


def _page(number: int, text: str) -> PdfPage:
    """Create a lightweight PDF-page model for text-analysis tests."""
    root = Path("/tmp")
    return PdfPage(
        number=number,
        image_path=root / f"pdf_structure_{number}.png",
        thumbnail_path=root / f"pdf_structure_thumb_{number}.png",
        extracted_text=text,
        source_type="pdf",
    )


def test_local_pdf_selection_discards_reference_content_and_keeps_technical_pages() -> None:
    pages = [
        _page(1, "Índice\nTable of contents\nPágina de referência"),
        _page(2, "Safety warning: disconnect the equipment before maintenance."),
        _page(3, "Installation and wiring instructions for the control cabinet."),
        _page(4, "Operation: start the system and check the status indicators."),
        _page(5, "Technical data\nRated voltage: 400 V\nCurrent: 16 A"),
        _page(6, "Maintenance schedule and troubleshooting of common faults."),
    ]

    plan = ManualAIService().create_pdf_structure(pages, "Motor controller")

    assert plan.sections
    assert 1 in plan.omitted_page_numbers
    assert set(plan.selected_page_numbers).issubset({2, 3, 4, 5, 6})
    assert len(plan.selected_page_numbers) == len(set(plan.selected_page_numbers))
    assert any(section.title == "Segurança" for section in plan.sections)
    assert any(section.title == "Dados técnicos" for section in plan.sections)
    assert all(section.evidence for section in plan.sections)


def test_ai_structure_parser_rejects_invalid_or_duplicate_page_references() -> None:
    pages = [
        _page(2, "Safety warning: disconnect the equipment before maintenance."),
        _page(3, "Installation instructions: mount the control cabinet correctly."),
        _page(4, "Operation procedure: start the system and observe indicators."),
    ]
    payload = {
        "document_title": "Painel de controle",
        "sections": [
            {
                "title": "Segurança",
                "intro": "Verifique as proteções antes do uso.",
                "evidence": "disconnect the equipment before maintenance",
                "pages": [2, 2, 999],
                "subsections": [
                    {
                        "title": "Instalação",
                        "intro": "Monte corretamente.",
                        "evidence": "mount the control cabinet correctly",
                        "pages": [3, 2],
                    },
                ],
            },
            {
                "title": "Operação",
                "evidence": "start the system and observe indicators",
                "pages": [4],
            },
        ],
    }

    plan = ManualAIService()._parse_pdf_structure(json.dumps(payload), pages, "Manual")

    assert plan.document_title == "Painel de controle"
    assert plan.selected_page_numbers == [2, 3, 4]
    assert plan.sections[0].page_numbers == [2]
    assert plan.sections[0].subsections[0].page_numbers == [3]
    assert plan.sections[1].page_numbers == [4]


def test_ai_structure_parser_rejects_generic_sections_without_page_evidence() -> None:
    pages = [
        _page(1, "Motor overload protection is configured through the relay settings."),
        _page(2, "Connect the control cable to terminal X1 before energizing the panel."),
    ]
    payload = {
        "document_title": "Manual genérico",
        "sections": [
            {"title": "Introdução", "intro": "Visão geral do sistema.", "pages": [1]},
            {"title": "Operação", "intro": "Use o equipamento conforme instruções.", "pages": [2]},
        ],
    }

    plan = ManualAIService()._parse_pdf_structure(json.dumps(payload), pages, "Manual")

    assert plan.sections == []
    assert plan.selected_page_numbers == []


def test_source_heading_structure_keeps_complete_essential_chapter_ranges() -> None:
    pages = [
        _page(1, "Table of contents\n2 Safety\n3 Installation\n4 Operation\n5 Maintenance\n6 Technical data"),
        _page(2, "2\nSafety\n2.1\nImportant information\nRead the safety information before operating the pump."),
        _page(3, "2\nSafety\n2.2\nSafety precautions\nDisconnect power before maintenance."),
        _page(4, "3\nInstallation\n3.1\nUnpacking/delivery\nCheck the delivery and inspect the pump."),
        _page(5, "3 Installation\n3.2 Installation\nFit the pump in the process line."),
        _page(6, "4\nOperation\n4.1\nControls\nStart the pump and inspect the controls."),
        _page(7, "4\nOperation\n4.2\nTroubleshooting\nCheck the fault condition before restarting."),
        _page(8, "5 Maintenance\n5.1 General maintenance\nInspect seals and bearings."),
        _page(9, "5 Maintenance\n5.2 Motor maintenance\nLubricate according to the motor manual."),
        _page(10, "6 Technical data\n6.1 Technical data\nMaximum pressure and temperature limits."),
        _page(11, "7 Parts list and service kits\nService kits are listed here."),
    ]

    plan = ManualAIService().create_pdf_structure(pages, "Bomba LKH")

    assert [section.title for section in plan.sections] == [
        "Segurança", "Instalação", "Operação", "Manutenção", "Dados técnicos", "Peças e kits de serviço"
    ]
    assert plan.detected_chapter_ranges["Segurança"] == [2, 3]
    assert plan.detected_chapter_ranges["Instalação"] == [4, 5]
    assert plan.detected_chapter_ranges["Operação"] == [6, 7]
    assert plan.detected_chapter_ranges["Manutenção"] == [8, 9]
    assert plan.detected_chapter_ranges["Dados técnicos"] == [10]
    assert plan.detected_chapter_ranges["Peças e kits de serviço"] == [11]
    assert plan.selected_page_numbers == list(range(2, 12))
    assert 1 in plan.omitted_page_numbers
    assert [subsection.title for subsection in plan.sections[0].subsections] == [
        "Informações importantes", "Precauções de segurança"
    ]
    assert plan.sections[2].subsections[0].title == "Controles"
    assert plan.sections[2].subsections[1].title == "Solução de problemas"


def test_translation_cleanup_keeps_only_the_final_translated_content() -> None:
    raw = """Não há necessidade de tradução, pois o texto já está em português.
TEXT: Safety is fundamental when working with the pump.
Tradução:
A segurança é fundamental ao trabalhar com a bomba.
"""

    result = ManusTranslationService._clean_model_output(raw)

    assert result == "A segurança é fundamental ao trabalhar com a bomba."
    assert "TEXT:" not in result
    assert "Não há necessidade" not in result


def test_rmarkdown_formatter_removes_ai_metacommentary_from_saved_text_blocks() -> None:
    raw = """TEXT: Original safety instruction.
Tradução:
- Desconecte a alimentação antes da manutenção.
"""

    result = ProjectExportService._format_rmd_text(raw)

    assert result == "- Desconecte a alimentação antes da manutenção."
    assert "TEXT:" not in result
    assert "Tradução:" not in result


def test_rmarkdown_formatter_removes_duplicate_source_chapter_and_preserves_subheading() -> None:
    raw = """2 Segurança Práticas inseguras e outras informações importantes são enfatizadas.
# 2 Segurança
## 2.1 Informações importantes
### AVISO
Desconecte a alimentação antes da manutenção.
"""

    result = ProjectExportService._format_rmd_text(raw, context_title="Segurança")

    assert "# 2 Segurança" not in result
    assert "Práticas inseguras" in result
    assert "### Informações importantes" in result
    assert "#### AVISO" in result


def test_rmarkdown_formatter_recovers_a_table_collapsed_into_one_line() -> None:
    raw = "Verifique a entrega: | Item | Descrição | --- | --- | 1 | Bomba completa | 2 | Nota de entrega |"

    result = ProjectExportService._format_rmd_text(raw)

    assert "Verifique a entrega:" in result
    assert "| Item | Descrição |" in result
    assert "| 1 | Bomba completa |" in result
    assert "| 2 | Nota de entrega |" in result


def test_structured_translation_splits_dense_source_text_on_safe_boundaries() -> None:
    source = ("Linha técnica com valor nominal e procedimento de manutenção.\n" * 180).strip()

    chunks = ManusTranslationService._source_text_chunks(source, maximum_characters=500)

    assert len(chunks) > 1
    assert all(len(chunk) <= 500 for chunk in chunks)
    assert "procedimento de manutenção" in "\n".join(chunks)


def test_layout_detection_routes_repeated_or_collapsed_pdf_text_to_visual_reading() -> None:
    assert ManusTranslationService._requires_visual_layout_reconstruction(
        """Etapa
Etapa
Etapa
Sempre leia os dados técnicos."""
    )
    assert ManusTranslationService._requires_visual_layout_reconstruction(
        "| Item | Descrição | --- | --- | 1 | Bomba |"
    )
    assert not ManusTranslationService._requires_visual_layout_reconstruction(
        """Desconecte a alimentação antes da manutenção.
Use peças genuínas."""
    )


def test_text_outline_parser_builds_sections_with_real_page_evidence() -> None:
    pages = [
        _page(2, "Safety warning: disconnect the equipment before maintenance."),
        _page(3, "Installation and wiring instructions for the control cabinet."),
        _page(4, "Table of contents and document references."),
    ]
    raw = """
    1. Segurança — páginas 2
    2. Instalação e ligação — páginas 3
    3. Referências — páginas 4
    """

    plan = ManualAIService()._parse_pdf_structure(raw, pages, "Painel de controle")

    assert [section.title for section in plan.sections] == ["Segurança", "Instalação e ligação"]
    assert plan.selected_page_numbers == [2, 3]
    assert "disconnect the equipment" in plan.sections[0].evidence
    assert "installation and wiring" in plan.sections[1].evidence
    assert 4 in plan.omitted_page_numbers

    markdown_plan = ManualAIService()._parse_pdf_structure(
        "### **Segurança** — pág. 2\n- **Instalação e ligação** — páginas 3",
        pages,
        "Painel de controle",
    )
    assert [section.page_numbers for section in markdown_plan.sections] == [[2], [3]]
    assert all(section.evidence for section in markdown_plan.sections)


def test_text_outline_parser_rejects_generic_or_unmatched_titles() -> None:
    pages = [_page(2, "Safety warning: disconnect the equipment before maintenance.")]

    plan = ManualAIService()._parse_pdf_structure(
        "1. Introdução geral — páginas 2", pages, "Painel de controle"
    )

    assert plan.sections == []
    assert plan.selected_page_numbers == []


def test_pdf_plan_classifies_textual_and_graphical_pages_in_main_window() -> None:
    dense_text = (
        "Safety precautions must be followed before operating the pump. "
        "Disconnect the electrical supply before maintenance and verify that the process line "
        "is depressurized. Operators must use approved protective equipment and report damage. "
    ) * 4
    pages = [
        _page(2, dense_text),
        _page(3, "Warning symbols\nFigure 3\nCaution\nDanger"),
    ]
    plan = PdfStructurePlan(
        document_title="Manual de teste",
        sections=[
            PdfStructureSection(
                title="Segurança",
                intro="Leia as instruções antes de operar.",
                page_numbers=[2],
                subsections=[
                    PdfStructureSubsection(
                        title="Montagem",
                        intro="Fixe o equipamento em superfície adequada.",
                        page_numbers=[3],
                    )
                ],
            )
        ],
        selected_page_numbers=[2, 3],
    )

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    try:
        window._pages = pages
        assert window._build_sections_from_pdf_plan(plan) == 1
        section = window._sections[0]
        subsection = section.subsections[0]
        assert section.content[0] == "Leia as instruções antes de operar."
        assert isinstance(section.content[1], PdfPage)
        assert section.content[1].export_mode == "text"
        assert subsection.content[0] == "Fixe o equipamento em superfície adequada."
        assert isinstance(subsection.content[1], PdfPage)
        # A decisão final de preservar uma ilustração é da leitura visual na exportação.
        # Um rótulo curto como "Figure" não pode rebaixar uma página técnica para imagem.
        assert subsection.content[1].export_mode == "text"
    finally:
        window.close()
        app.processEvents()


def test_pdf_plan_sends_scanned_pages_to_visual_text_reconstruction() -> None:
    pages = [_page(2, "")]
    plan = PdfStructurePlan(
        document_title="Manual escaneado",
        sections=[PdfStructureSection(title="Segurança", page_numbers=[2])],
        selected_page_numbers=[2],
    )

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    try:
        window._pages = pages
        assert window._build_sections_from_pdf_plan(plan) == 1
        page = window._sections[0].content[0]
        assert isinstance(page, PdfPage)
        assert page.export_mode == "text"
    finally:
        window.close()
        app.processEvents()


def test_window_reports_missing_pages_from_detected_chapter_coverage() -> None:
    pages = [
        _page(2, "2 Safety\nRead all safety instructions."),
        _page(3, "2 Safety\nDisconnect power before maintenance."),
    ]
    plan = PdfStructurePlan(
        document_title="Bomba",
        sections=[PdfStructureSection(title="Segurança", page_numbers=[2])],
        selected_page_numbers=[2, 3],
        detected_chapter_ranges={"Segurança": [2, 3]},
    )

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    try:
        window._pages = pages
        window._last_pdf_structure_plan = plan
        window._build_sections_from_pdf_plan(plan)
        warnings = window._automatic_plan_coverage_warnings()
        assert any("páginas técnicas reconhecidas" in warning.lower() for warning in warnings)
        assert any("3" in warning for warning in warnings)
    finally:
        window.close()
        app.processEvents()


def test_scanned_pdf_pages_receive_visual_text_before_structure_analysis() -> None:
    pages = [
        _page(1, ""),
        _page(2, ""),
        _page(3, "Selectable technical content with rated current, voltage, installation torque and terminal identification. " * 5),
    ]
    worker = PdfStructureWorker(
        pages,
        "Manual",
        "test-key",
        "https://api.groq.com/openai/v1",
        "llama-3.3-70b-versatile",
    )
    assert [page.number for page in worker._pages_needing_visual_read(pages)] == [1, 2]

    original = ManusTranslationService.extract_page_outline_text
    ManusTranslationService.extract_page_outline_text = (
        lambda _service, source: (
            "Safety warning: disconnect power before maintenance."
            if source.name.endswith("_1.png")
            else "Installation wiring and commissioning procedure."
        )
    )
    try:
        assert worker._supplement_visual_text() == 2
    finally:
        ManusTranslationService.extract_page_outline_text = original

    assert "disconnect power" in worker._pages[0].extracted_text.lower()
    assert "commissioning" in worker._pages[1].extracted_text.lower()

    plan = ManualAIService().create_pdf_structure(worker._pages, "Manual escaneado")
    assert plan.sections
    assert {section.title for section in plan.sections} >= {"Segurança", "Instalação e comissionamento"}


def test_pdf_plan_replaces_generic_ai_intro_with_selected_page_content() -> None:
    pages = [
        _page(
            2,
            "Safety warning: disconnect the equipment before maintenance. "
            "Never service the equipment while hot.",
        ),
    ]
    payload = {
        "document_title": "Bomba",
        "sections": [
            {
                "title": "Segurança",
                "intro": "A segurança é fundamental ao trabalhar com a bomba.",
                "evidence": "disconnect the equipment before maintenance",
                "pages": [2],
            }
        ],
    }

    plan = ManualAIService()._parse_pdf_structure(json.dumps(payload), pages, "Bomba")

    assert plan.sections[0].intro.startswith("Safety warning")
    assert "é fundamental" not in plan.sections[0].intro


def test_local_grouping_keeps_related_pages_and_uses_source_backed_intro() -> None:
    pages = [
        _page(1, "Safety warning: disconnect the equipment before maintenance."),
        _page(2, "Caution: never touch the pump while it is hot."),
        _page(
            3,
            "General maintenance. Replace worn seals and inspect the motor guard every 12 months.",
        ),
    ]

    plan = ManualAIService().create_pdf_structure(pages, "Bomba")
    sections = {section.title: section for section in plan.sections}

    assert sections["Segurança"].page_numbers == [1, 2]
    assert sections["Manutenção e diagnóstico"].page_numbers == [3]
    assert "Conteúdo técnico selecionado" not in sections["Segurança"].intro
    assert "Safety warning" in sections["Segurança"].intro


def test_local_selection_uses_a_real_heading_when_no_category_matches() -> None:
    pages = [
        _page(
            1,
            "GX2000 Controller Overview\n"
            "This controller provides adjustable parameter monitoring and system communication. " * 4,
        )
    ]

    plan = ManualAIService().create_pdf_structure(pages, "Manual do controlador")

    assert plan.sections
    assert plan.sections[0].title == "GX2000 Controller Overview"
    assert plan.sections[0].evidence


def test_empty_pdf_text_explains_that_visual_read_is_required() -> None:
    plan = ManualAIService().create_pdf_structure([_page(1, "")], "Manual escaneado")

    assert not plan.sections
    assert "leitura visual" in plan.note.lower()


def test_ai_suggestion_shows_only_the_saved_evidence_based_pdf_selection() -> None:
    pages = [_page(2, "Safety warning: disconnect the equipment before maintenance.")]
    plan = PdfStructurePlan(
        document_title="Painel de teste",
        sections=[
            PdfStructureSection(
                title="Segurança",
                page_numbers=[2],
                evidence="disconnect the equipment before maintenance",
            )
        ],
        selected_page_numbers=[2],
        used_ai=True,
    )
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    try:
        window._pages = pages
        window._last_pdf_structure_plan = plan
        window.ai_suggest_structure()
        rendered_text = window.chat_display.toPlainText()
        assert "Seleção fundamentada do PDF" in rendered_text
        assert "páginas 2" in rendered_text
        assert "disconnect the equipment before maintenance" in rendered_text
        assert "Sugestão de Estrutura da IA" not in rendered_text
    finally:
        window.close()
        app.processEvents()


class _StructuredTranslator:
    """Deterministic translator fixture that returns already-extracted technical content."""

    supports_page_translation = True

    def translate_page(self, source: Path, target: Path, target_language: str) -> None:
        target.write_bytes(source.read_bytes())

    def extract_structured_content(
        self,
        source: Path,
        target_language: str,
        source_text: str = "",
    ) -> str:
        return "Tensão nominal: 400 V\nCorrente nominal: 16 A\n\n• Desconecte a alimentação."


class _EmptyStructuredTranslator:
    """Translator fixture that simulates a failed textual extraction."""

    supports_page_translation = True

    def translate_page(self, source: Path, target: Path, target_language: str) -> None:
        target.write_bytes(source.read_bytes())

    def extract_structured_content(
        self,
        source: Path,
        target_language: str,
        source_text: str = "",
    ) -> str:
        return ""


class _GraphicOnlyTranslator:
    """Translator fixture that classifies a visual-only page as an illustration."""

    supports_page_translation = True

    def translate_page(self, source: Path, target: Path, target_language: str) -> None:
        target.write_bytes(source.read_bytes())

    def extract_structured_content(
        self,
        source: Path,
        target_language: str,
        source_text: str = "",
    ) -> str:
        return "[[KEEP_AS_IMAGE]]"


def test_rmarkdown_formatter_creates_tables_and_normalizes_lists() -> None:
    source = """Tensão nominal: 400 V
Corrente nominal: 16 A
Frequência: 50 Hz

• Desconecte o equipamento.
* Verifique os terminais.
1) Ligue a alimentação."""

    result = ProjectExportService._format_rmd_text(source)

    assert "| Item | Descrição |" in result
    assert "| Tensão nominal | 400 V |" in result
    assert "- Desconecte o equipamento." in result
    assert "- Verifique os terminais." in result
    assert "1. Ligue a alimentação." in result


def test_text_mode_pdf_page_exports_as_formatted_content() -> None:
    with TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        source = root / "technical_page.png"
        source.write_bytes(b"not-a-real-image-but-copyable")
        page = PdfPage(
            number=1,
            image_path=source,
            thumbnail_path=source,
            extracted_text="Tensão nominal: 400 V\nCorrente nominal: 16 A",
            export_mode="text",
            source_type="pdf",
        )
        export = ProjectExportService()
        export._write_language_project(
            root / "manual",
            "Manual de teste",
            [ManualSection(title="Dados técnicos", content=[page])],
            "T-001",
            "2026-08",
            "pt",
            translator=_StructuredTranslator(),
            translate_images=True,
        )
        rmd = (root / "manual" / "manual.rmd").read_text(encoding="utf-8")

    assert "| Item | Descrição |" in rmd
    assert "| Tensão nominal | 400 V |" in rmd
    assert "- Desconecte a alimentação." in rmd
    assert "include_graphics('img/technical_page.png')" not in rmd


def test_text_mode_page_never_falls_back_to_an_english_image() -> None:
    with TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        source = root / "textual_page.png"
        source.write_bytes(b"copyable-text-page")
        page = PdfPage(
            number=9,
            image_path=source,
            thumbnail_path=source,
            extracted_text="Safety procedure",
            export_mode="text",
            source_type="pdf",
        )
        try:
            ProjectExportService()._write_language_project(
                root / "manual",
                "Manual de teste",
                [ManualSection(title="Segurança", content=[page])],
                "T-004",
                "2026-08",
                "pt",
                translator=_EmptyStructuredTranslator(),
                translate_images=True,
            )
            raise AssertionError("A exportação deveria interromper uma página textual sem extração.")
        except TranslationError as error:
            assert "página 9" in str(error)
            assert "inglês como imagem" in str(error)


def test_visual_marker_preserves_only_the_graphic_page_as_image() -> None:
    with TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        source = root / "technical_drawing.png"
        source.write_bytes(b"copyable-drawing")
        page = PdfPage(
            number=1,
            image_path=source,
            thumbnail_path=source,
            extracted_text="",
            export_mode="text",
            source_type="pdf",
        )
        export = ProjectExportService()
        export._write_language_project(
            root / "manual",
            "Manual de teste",
            [ManualSection(title="Desenho", content=[page])],
            "T-003",
            "2026-08",
            "pt",
            translator=_GraphicOnlyTranslator(),
            translate_images=True,
        )
        rmd = (root / "manual" / "manual.rmd").read_text(encoding="utf-8")

    assert "[[KEEP_AS_IMAGE]]" not in rmd
    assert "knitr::include_graphics('img/" in rmd


def test_rmarkdown_formatter_removes_nested_duplicate_headings_and_contact_fragments() -> None:
    source = """# 2 Segurança
## 2.2 Precauções de segurança
Desconecte a alimentação antes de abrir a bomba.
## Como contatar
### Alfa Laval
Telefone: +46 0 0
"""

    result = ProjectExportService._format_rmd_text(
        source,
        context_title="Segurança\nPrecauções de segurança",
    )

    assert "# 2 Segurança" not in result
    assert "Precauções de segurança" not in result
    assert "Como contatar" not in result
    assert "Alfa Laval" not in result
    assert "Desconecte a alimentação" in result


def test_image_pages_use_safe_width_and_no_html_tabsets() -> None:
    with TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        source = root / "visual_page.png"
        source.write_bytes(b"copyable-image")
        page = PdfPage(
            number=1,
            image_path=source,
            thumbnail_path=source,
            extracted_text="",
            export_mode="image",
            source_type="pdf",
        )
        export = ProjectExportService()
        export._write_language_project(
            root / "manual",
            "Manual de teste",
            [ManualSection(title="Operação", content=[page])],
            "T-002",
            "2026-08",
            "pt",
        )
        rmd = (root / "manual" / "manual.rmd").read_text(encoding="utf-8")

    assert "out.width='94%'" in rmd
    assert "out.height=" not in rmd
    assert "fig.pos='H'" in rmd
    assert "{.tabset" not in rmd
    assert "\\setmainfont{Gotham Rounded Book}" in rmd
    assert "\\vspace{2.2cm}" in rmd
    assert "\\vspace{4cm}\n\\newpage" not in rmd
    assert rmd.count("\\newpage") == 1
    assert "library(rsvg)" not in rmd


if __name__ == "__main__":
    test_local_pdf_selection_discards_reference_content_and_keeps_technical_pages()
    test_ai_structure_parser_rejects_invalid_or_duplicate_page_references()
    test_source_heading_structure_keeps_complete_essential_chapter_ranges()
    test_translation_cleanup_keeps_only_the_final_translated_content()
    test_rmarkdown_formatter_removes_ai_metacommentary_from_saved_text_blocks()
    test_rmarkdown_formatter_removes_duplicate_source_chapter_and_preserves_subheading()
    test_rmarkdown_formatter_recovers_a_table_collapsed_into_one_line()
    test_structured_translation_splits_dense_source_text_on_safe_boundaries()
    test_layout_detection_routes_repeated_or_collapsed_pdf_text_to_visual_reading()
    test_text_outline_parser_builds_sections_with_real_page_evidence()
    test_text_outline_parser_rejects_generic_or_unmatched_titles()
    test_scanned_pdf_pages_receive_visual_text_before_structure_analysis()
    test_local_selection_uses_a_real_heading_when_no_category_matches()
    test_pdf_plan_replaces_generic_ai_intro_with_selected_page_content()
    test_local_grouping_keeps_related_pages_and_uses_source_backed_intro()
    test_empty_pdf_text_explains_that_visual_read_is_required()
    test_pdf_plan_classifies_textual_and_graphical_pages_in_main_window()
    test_pdf_plan_sends_scanned_pages_to_visual_text_reconstruction()
    test_window_reports_missing_pages_from_detected_chapter_coverage()
    test_ai_suggestion_shows_only_the_saved_evidence_based_pdf_selection()
    test_rmarkdown_formatter_creates_tables_and_normalizes_lists()
    test_text_mode_pdf_page_exports_as_formatted_content()
    test_text_mode_page_never_falls_back_to_an_english_image()
    test_visual_marker_preserves_only_the_graphic_page_as_image()
    test_rmarkdown_formatter_removes_nested_duplicate_headings_and_contact_fragments()
    test_image_pages_use_safe_width_and_no_html_tabsets()
    print("PDF structure tests passed")
