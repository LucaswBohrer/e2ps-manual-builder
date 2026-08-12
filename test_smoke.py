"""Smoke test for E2PS Manual Builder services."""

from pathlib import Path
from manual_builder.models import PdfPage, ManualSection, ManualSubsection
from manual_builder.translation_service import create_translation_service

def test_imports():
    print("Testing basic imports and models...")
    page = PdfPage(number=1, image_path=Path("dummy.png"), thumbnail_path=Path("thumb.png"), variant=1)
    assert page.filename == "page_001.png"
    assert page.display_name == "Page 001"
    
    subsection = ManualSubsection(title="Sub 1", pages=[page])
    section = ManualSection(title="Sec 1", pages=[page], subsections=[subsection])
    assert section.title == "Sec 1"
    print("Models test passed.")

def test_translation_service():
    print("Testing translation service creation...")
    service = create_translation_service("manus", "", "", "pt")
    assert service.supports_page_translation is True
    translated = service.translate_text("Installation", "pt")
    assert translated == "Installation"
    print("Translation service test passed.")

if __name__ == "__main__":
    test_imports()
    test_translation_service()
    print("All smoke tests passed successfully!")
