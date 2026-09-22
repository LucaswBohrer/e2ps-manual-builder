from pathlib import Path
from tempfile import TemporaryDirectory

from manual_builder.models import ManualSection, PdfPage
from manual_builder.project_service import ProjectExportService
from manual_builder.project_file_service import ProjectFileService


def main() -> None:
    with TemporaryDirectory(prefix="operational_test_") as raw:
        root = Path(raw)
        page_path = root / "page.png"
        page_path.write_bytes(b"not-an-image-but-copyable")
        page = PdfPage(
            number=1,
            image_path=page_path,
            thumbnail_path=page_path,
            extracted_text="",
            export_mode="image",
            figure_caption="Tela principal",
            figure_width="50%",
            figure_alignment="left",
        )
        sections = [ManualSection("EQUIPO", ["Texto específico", page])]
        metadata = {
            "title": "E2SOLID",
            "manual_type": "operational",
            "source_language": "pt",
            "revision": "01",
            "equipment_type": "Sistema de preparo",
            "model": "E2SOLID",
            "serial_year": "2026",
            "objective": "Objetivo editável",
            "safety": "Segurança editável",
            "control": "Controle editável",
            "equipment_operation": "Funcionamento editável",
            "equipment_functions": "Funções editáveis",
        }
        output = ProjectExportService().export_multilingual(
            root,
            "E2SOLID",
            sections,
            ["pt"],
            "pt",
            "manus",
            "",
            "",
            "E2SOLID",
            "2026-02",
            lambda *_: None,
            manual_type="operational",
            operational_metadata=metadata,
        )
        rmd = (output / "Português" / "manual.rmd").read_text(encoding="utf-8")
        assert "Manual Operacional" in rmd
        assert "Objetivo editável" in rmd
        assert "Funcionamento editável" in rmd
        assert "out.width='50%'" in rmd
        assert "fig.align='left'" in rmd
        assert "fig.cap='Tela principal'" in rmd
        assert (output / "Português" / "img" / "page_001.png").is_file()

        archive = ProjectFileService().save_project(
            root / "operational.e2ps", [page], sections, metadata, None
        )
        restored = ProjectFileService().load_project(archive, root / "restored")
        assert restored.metadata["manual_type"] == "operational"
        restored_page = restored.pages[0]
        assert restored_page.figure_caption == "Tela principal"
        assert restored_page.figure_width == "50%"
        assert restored_page.figure_alignment == "left"

    print("OK: operational template, figure layout and V3 persistence validated")


if __name__ == "__main__":
    main()
