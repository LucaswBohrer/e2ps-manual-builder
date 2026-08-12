"""Smoke test for E2PS Manual Builder services including AI features."""

from pathlib import Path
from manual_builder.models import PdfPage, ManualSection, ManualSubsection
from manual_builder.ai_service import ManualAIService

def test_ai_models():
    print("Testing AI models and text blocks...")
    page = PdfPage(number=1, image_path=Path("dummy.png"), thumbnail_path=Path("thumb.png"), variant=1)
    section = ManualSection(title="Sec 1", pages=[page], text_content="Intro text")
    assert section.text_content == "Intro text"

    ai = ManualAIService()
    struct = ai.suggest_structure([page], "Test Manual")
    assert len(struct) > 0
    print("AI models test passed successfully.")

if __name__ == "__main__":
    test_ai_models()
    print("All smoke tests passed!")
