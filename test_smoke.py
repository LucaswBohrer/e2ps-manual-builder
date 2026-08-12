"""Smoke test for E2PS Manual Builder services including AI chat and mixed content blocks."""

from pathlib import Path
from manual_builder.models import PdfPage, ManualSection, ManualSubsection
from manual_builder.ai_service import ManualAIService

def test_mixed_content_and_ai():
    print("Testing mixed content models and AI chat...")
    page = PdfPage(number=1, image_path=Path("dummy.png"), thumbnail_path=Path("thumb.png"), variant=1)
    
    # Section with mixed content: text before, page image, text after
    section = ManualSection(
        title="Instalação",
        content=["Texto introdutório antes da imagem", page, "Texto explicativo após a imagem"]
    )
    assert len(section.content) == 3
    assert isinstance(section.content[0], str)
    assert isinstance(section.content[1], PdfPage)

    ai = ManualAIService()
    reply = ai.ask_ai("Olá, qual página devo usar para a introdução?", "Pág 1, Pág 2")
    assert isinstance(reply, str)
    print("Mixed content and AI chat test passed successfully.")

if __name__ == "__main__":
    test_mixed_content_and_ai()
    print("All smoke tests passed!")
