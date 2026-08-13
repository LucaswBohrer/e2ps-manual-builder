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
from manual_builder.translation_service import ManusTranslationService
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


def test_pdf_plan_creates_editable_text_mode_content_in_main_window() -> None:
    pages = [_page(2, "Safety"), _page(3, "Installation")]
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
        assert subsection.content[1].export_mode == "text"
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


if __name__ == "__main__":
    test_local_pdf_selection_discards_reference_content_and_keeps_technical_pages()
    test_ai_structure_parser_rejects_invalid_or_duplicate_page_references()
    test_text_outline_parser_builds_sections_with_real_page_evidence()
    test_text_outline_parser_rejects_generic_or_unmatched_titles()
    test_scanned_pdf_pages_receive_visual_text_before_structure_analysis()
    test_local_selection_uses_a_real_heading_when_no_category_matches()
    test_empty_pdf_text_explains_that_visual_read_is_required()
    test_pdf_plan_creates_editable_text_mode_content_in_main_window()
    test_ai_suggestion_shows_only_the_saved_evidence_based_pdf_selection()
    test_rmarkdown_formatter_creates_tables_and_normalizes_lists()
    test_text_mode_pdf_page_exports_as_formatted_content()
    print("PDF structure tests passed")
