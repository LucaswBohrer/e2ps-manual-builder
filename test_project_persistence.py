from __future__ import annotations

import os
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PIL import Image
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from manual_builder.main_window import MainWindow
from manual_builder.models import ManualSection, ManualSubsection, PdfPage
from manual_builder.project_file_service import ProjectFileService


def create_image(path: Path, color: str, size: tuple[int, int]) -> None:
    Image.new("RGB", size, color=color).save(path, "PNG")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="emb_test_") as raw_dir:
        root = Path(raw_dir)
        source_dir = root / "source"
        source_dir.mkdir()
        image_1 = source_dir / "page_001_01.png"
        thumb_1 = source_dir / "thumbnail_001_01.png"
        image_2 = source_dir / "page_001_crop_02.png"
        thumb_2 = source_dir / "thumbnail_001_crop_02.png"
        cover = source_dir / "cover.png"
        create_image(image_1, "red", (240, 160))
        create_image(thumb_1, "red", (120, 80))
        create_image(image_2, "blue", (160, 120))
        create_image(thumb_2, "blue", (120, 90))
        create_image(cover, "green", (200, 300))

        page_1 = PdfPage(1, image_1, thumb_1, 1, "Texto da página 1", "text")
        page_2 = PdfPage(1, image_2, thumb_2, 2, "Recorte da página 1", "image")
        sections = [
            ManualSection(
                title="Dados técnicos",
                content=["Texto introdutório", page_1, page_2],
                subsections=[ManualSubsection("Limites", [page_2, "Observação final"])],
            )
        ]
        metadata = {
            "title": "Manual de Teste",
            "code": "04888",
            "year": "2026",
            "semester": "01",
            "source_language": "en",
            "languages": {"pt": True, "en": False, "es": True},
        }

        service = ProjectFileService()
        archive = service.save_project(root / "manual_teste.e2ps", [page_1, page_2], sections, metadata, cover)
        assert archive.is_file(), "O arquivo .e2ps não foi criado."
        restored = service.load_project(archive, root / "restored")

        assert len(restored.pages) == 2
        assert restored.pages[0].export_mode == "text"
        assert restored.pages[1].variant == 2
        assert restored.pages[0].image_path.is_file()
        assert restored.pages[1].thumbnail_path.is_file()
        assert restored.cover_image_path and restored.cover_image_path.is_file()
        assert restored.metadata == metadata
        assert restored.sections[0].title == "Dados técnicos"
        assert restored.sections[0].content[0] == "Texto introdutório"
        assert isinstance(restored.sections[0].content[1], PdfPage)
        assert restored.sections[0].subsections[0].content[1] == "Observação final"

        app = QApplication.instance() or QApplication([])
        window = MainWindow()
        assert window.open_e2ps_project_file(archive)
        assert window._project_path == archive
        assert len(window._pages) == 2
        assert window._sections[0].title == "Dados técnicos"

        window._settings = QSettings(str(root / "settings.ini"), QSettings.Format.IniFormat)
        window.api_key_input.setText("gsk_test_local_only")
        window.base_url_input.setText("https://api.groq.com/openai/v1")
        window.model_input.setText("llama-3.3-70b-versatile")
        window._persist_ai_settings()
        window.api_key_input.clear()
        window.base_url_input.clear()
        window.model_input.clear()
        window._restore_ai_settings()
        assert window.api_key_input.text() == "gsk_test_local_only"
        assert window.base_url_input.text() == "https://api.groq.com/openai/v1"
        assert window.model_input.text() == "llama-3.3-70b-versatile"
        window.close()
        app.quit()

    print("OK: projeto .e2ps e persistência local de IA validados")


if __name__ == "__main__":
    main()
