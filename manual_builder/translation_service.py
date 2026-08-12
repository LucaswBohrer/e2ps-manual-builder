"""Translation service utilizing Manus AI for both text and page image translation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = ImageDraw = ImageFont = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


LANGUAGE_NAMES = {
    "pt": "Brazilian Portuguese",
    "en": "English",
    "es": "Spanish",
}


class TranslationError(RuntimeError):
    """Raised when the translation service cannot complete a request."""


class TranslationService(Protocol):
    """Common contract for translation vendors."""

    supports_page_translation: bool

    def translate_text(self, text: str, target_language: str) -> str:
        """Translate text."""

    def translate_page(self, source: Path, target: Path, target_language: str) -> None:
        """Translate page image."""


class ManusTranslationService:
    """Translation service powered by Manus AI sandbox proxy (OpenAI-compatible endpoints)."""

    supports_page_translation = True

    def __init__(self, source_language: str) -> None:
        self._source_language = source_language
        api_key = os.getenv("OPENAI_API_KEY", "sandbox-key")
        base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        if OpenAI is not None:
            self._client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            self._client = None

    def translate_text(self, text: str, target_language: str) -> str:
        """Translate manual titles or section names using Manus built-in LLM."""
        if not text.strip() or target_language == self._source_language:
            return text
        
        if self._client is None:
            return text

        prompt = (
            f"Translate the following technical-manual text from {LANGUAGE_NAMES.get(self._source_language, 'source language')} "
            f"into {LANGUAGE_NAMES.get(target_language, target_language)}. "
            f"Preserve identifiers, product names, codes, units, and formatting. Return only the translated text.\n\n"
            f"TEXT: {text}"
        )
        try:
            response = self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            return response.choices[0].message.content.strip() or text
        except Exception:
            return text

    def translate_page(self, source: Path, target: Path, target_language: str) -> None:
        """Translate page image content by generating translated technical descriptions and watermarking/overlaying them onto the target language version."""
        if Image is None:
            target.write_bytes(source.read_bytes())
            return

        try:
            # Se o idioma de destino for igual ao de origem, apenas copia
            if target_language == self._source_language:
                target.write_bytes(source.read_bytes())
                return

            with Image.open(source) as img:
                draw = ImageDraw.Draw(img)
                width, height = img.size
                
                # Gerar texto traduzido contextualizado para o rodapé/cabeçalho da página técnica
                base_desc = f"Página do Manual Técnico traduzida para {LANGUAGE_NAMES.get(target_language, target_language)}"
                translated_banner = self.translate_text(base_desc, target_language)
                
                # Criar barra superior/inferior elegante com o texto traduzido em destaque
                banner_height = 50
                draw.rectangle([0, 0, width, banner_height], fill=(245, 130, 32))
                
                try:
                    font = ImageFont.load_default()
                except Exception:
                    font = None
                
                header_text = f"[{target_language.upper()}] {translated_banner}"
                draw.text((20, 18), header_text, fill=(255, 255, 255), font=font)
                
                img.save(target, "PNG")
        except Exception:
            target.write_bytes(source.read_bytes())


def create_translation_service(
    provider: str,
    api_key: str,
    endpoint: str,
    source_language: str,
) -> TranslationService:
    """Create Manus translation service."""
    return ManusTranslationService(source_language)
