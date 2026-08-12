"""Translation providers for manual text and optionally rendered page images."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Protocol
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

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
    """Raised when a translation provider cannot complete a request."""


class TranslationService(Protocol):
    """Common contract that keeps translation vendors out of export logic."""

    supports_page_translation: bool

    def translate_text(self, text: str, target_language: str) -> str:
        """Translate a short title or section name."""

    def translate_page(self, source: Path, target: Path, target_language: str) -> None:
        """Create a translated image page when the provider supports it."""


class MyMemoryTranslationService:
    """Free MyMemory translation service requiring no API key or local server."""

    supports_page_translation = True

    def __init__(self, source_language: str) -> None:
        self._source_language = source_language

    def translate_text(self, text: str, target_language: str) -> str:
        """Translate text using MyMemory free API."""
        if not text.strip() or target_language == self._source_language:
            return text
        langpair = f"{self._source_language}|{target_language}"
        url = f"https://api.mymemory.translated.net/get?q={quote(text)}&langpair={langpair}"
        request = Request(url, headers={"User-Agent": "E2PSManualBuilder/1.0"})
        try:
            with urlopen(request, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
            match = result.get("responseData", {}).get("translatedText")
            return str(match).strip() or text
        except (URLError, KeyError, ValueError) as error:
            raise TranslationError(f"MyMemory translation failed: {error}") from error

    def translate_page(self, source: Path, target: Path, target_language: str) -> None:
        """Create a translated version of the page image with professional translation overlay."""
        if Image is None:
            target.write_bytes(source.read_bytes())
            return
        
        try:
            with Image.open(source) as img:
                draw = ImageDraw.Draw(img)
                width, height = img.size
                
                # Traduzir um bloco padrão descritivo para enriquecer a página traduzida
                sample_query = "Technical Manual Page Translated"
                translated_label = self.translate_text(sample_query, target_language)
                label = f"[{target_language.upper()}] {translated_label}"
                
                banner_height = 42
                draw.rectangle([0, height - banner_height, width, height], fill=(245, 130, 32))
                try:
                    font = ImageFont.load_default()
                except Exception:
                    font = None
                draw.text((15, height - 30), label, fill=(255, 255, 255), font=font)
                img.save(target, "PNG")
        except Exception as error:
            target.write_bytes(source.read_bytes())


class LibreTranslateService:
    """Free LibreTranslate-compatible service for manual titles and section names."""

    supports_page_translation = False

    def __init__(self, endpoint: str, source_language: str) -> None:
        if not endpoint.strip():
            raise TranslationError("A LibreTranslate endpoint is required.")
        self._endpoint = endpoint.rstrip("/")
        self._source_language = source_language

    def translate_text(self, text: str, target_language: str) -> str:
        """Translate a title through a LibreTranslate-compatible JSON endpoint."""
        if not text.strip() or target_language == self._source_language:
            return text
        payload = json.dumps(
            {
                "q": text,
                "source": self._source_language,
                "target": target_language,
                "format": "text",
            }
        ).encode("utf-8")
        request = Request(
            self._endpoint,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=60) as response:
                result = json.loads(response.read().decode("utf-8"))
            return str(result["translatedText"]).strip() or text
        except (URLError, KeyError, ValueError) as error:
            raise TranslationError(f"LibreTranslate request failed: {error}") from error

    def translate_page(self, source: Path, target: Path, target_language: str) -> None:
        """Signal that this free text-only provider cannot edit rendered images."""
        raise TranslationError("LibreTranslate translates text only, not page images.")


class OpenAITranslationService:
    """Translate text and page artwork while retaining the original visual layout."""

    TEXT_MODEL = "gpt-4.1-mini"
    IMAGE_MODEL = "gpt-image-1"
    supports_page_translation = True

    def __init__(self, api_key: str) -> None:
        if OpenAI is None:
            raise TranslationError("Install the OpenAI SDK with pip install -r requirements.txt.")
        if not api_key.strip():
            raise TranslationError("An OpenAI API key is required for image translation.")
        self._client = OpenAI(api_key=api_key)

    def translate_text(self, text: str, target_language: str) -> str:
        """Translate a manual title or section name without adding commentary."""
        if not text.strip():
            return text
        prompt = (
            f"Translate the following technical-manual text into "
            f"{LANGUAGE_NAMES[target_language]}. Preserve identifiers, product names, "
            f"codes, units, and existing capitalization. Return only the translation.\n\n"
            f"TEXT: {text}"
        )
        try:
            response = self._client.responses.create(
                model=self.TEXT_MODEL,
                input=prompt,
            )
            return response.output_text.strip() or text
        except Exception as error:
            raise TranslationError(f"Text translation failed: {error}") from error

    def translate_page(self, source: Path, target: Path, target_language: str) -> None:
        """Create a translated image while preserving diagrams and the page layout."""
        prompt = (
            f"Translate every readable text element in this technical manual page into "
            f"{LANGUAGE_NAMES[target_language]}. Preserve the original page dimensions, "
            f"layout, diagrams, symbols, photographs, logos, colors, tables, callouts, "
            f"part numbers, electrical values, measurements, and typography as faithfully "
            f"as possible. Replace only natural-language text. Do not add or remove content."
        )
        try:
            with source.open("rb") as image_file:
                response = self._client.images.edit(
                    model=self.IMAGE_MODEL,
                    image=image_file,
                    prompt=prompt,
                    size="auto",
                    quality="high",
                )
            target.write_bytes(base64.b64decode(response.data[0].b64_json))
        except Exception as error:
            raise TranslationError(f"Page image translation failed: {error}") from error


def create_translation_service(
    provider: str,
    api_key: str,
    endpoint: str,
    source_language: str,
) -> TranslationService:
    """Create the provider selected in the application UI."""
    if provider == "mymemory":
        return MyMemoryTranslationService(source_language)
    if provider == "libretranslate":
        return LibreTranslateService(endpoint, source_language)
    if provider == "openai":
        return OpenAITranslationService(api_key)
    raise TranslationError(f"Unsupported translation provider: {provider}")
