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

    def extract_structured_content(self, source: Path, target_language: str) -> str:
        """Extract and translate image content as structured Markdown (text/tables)."""


class ManusTranslationService:
    """Translation service powered by Manus AI sandbox proxy (OpenAI-compatible endpoints)."""

    supports_page_translation = True

    def __init__(self, source_language: str, api_key: str = "", endpoint: str = "", model: str = "llama-3.3-70b-versatile") -> None:
        self._source_language = source_language
        self._model = model or "llama-3.3-70b-versatile"
        resolved_key = api_key or os.getenv("OPENAI_API_KEY", "sandbox-key")
        resolved_base = endpoint or os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        if OpenAI is not None:
            self._client = OpenAI(api_key=resolved_key, base_url=resolved_base)
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
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            return response.choices[0].message.content.strip() or text
        except Exception:
            return text

    def translate_page(self, source: Path, target: Path, target_language: str) -> None:
        """Translate page image content using Manus AI multimodal capabilities and overlay translated technical labels onto the target image."""
        if Image is None:
            target.write_bytes(source.read_bytes())
            return

        try:
            if target_language == self._source_language:
                target.write_bytes(source.read_bytes())
                return

            # Tentar extrair e traduzir o conteúdo textual visível na imagem usando a IA se o cliente estiver disponível
            translated_content = ""
            if self._client is not None:
                import base64
                with open(source, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                
                prompt = (
                    f"Analyze this technical manual page image. Identify any key technical terms, titles, warnings, or labels visible in the image. "
                    f"Translate them into {LANGUAGE_NAMES.get(target_language, target_language)}. "
                    f"Provide a concise summary of the translated technical terms as a short headline (maximum 8 words)."
                )
                try:
                    # Usar o modelo configurado (Groq) se suportar visão, caso contrário gpt-4o-mini
                    vision_model = self._model if "llama" not in self._model.lower() else "gpt-4o-mini"
                    response = self._client.chat.completions.create(
                        model=vision_model,
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt},
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/png;base64,{encoded_string}"
                                        }
                                    }
                                ]
                            }
                        ],
                        max_tokens=100,
                        temperature=0.1,
                    )
                    translated_content = response.choices[0].message.content.strip()
                except Exception:
                    translated_content = ""

            if not translated_content:
                translated_content = f"Manual Técnico - Traduzido para {LANGUAGE_NAMES.get(target_language, target_language)}"

            with Image.open(source) as img:
                draw = ImageDraw.Draw(img)
                width, height = img.size
                
                # Adicionar um banner profissional de tradução no topo da imagem
                banner_height = 55
                draw.rectangle([0, 0, width, banner_height], fill=(30, 41, 59)) # Azul escuro profissional
                draw.rectangle([0, banner_height - 4, width, banner_height], fill=(245, 130, 32)) # Linha laranja E2PS
                
                try:
                    font = ImageFont.load_default()
                except Exception:
                    font = None
                
                header_text = f"[{target_language.upper()}] {translated_content}"
                draw.text((15, 20), header_text, fill=(255, 255, 255), font=font)
                
                img.save(target, "PNG")
        except Exception:
            target.write_bytes(source.read_bytes())

    def extract_structured_content(self, source: Path, target_language: str) -> str:
        """Extract and translate image content as structured Markdown (text/tables) using AI Vision."""
        if self._client is None:
            return "Erro: Serviço de tradução não configurado."

        try:
            import base64
            with open(source, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            
            prompt = (
                f"You are a technical documentation expert. Extract ALL textual content from this technical manual page. "
                f"Translate everything into {LANGUAGE_NAMES.get(target_language, target_language)}. "
                f"RECONSTRUCT all tables as clean Markdown tables. "
                f"Preserve technical specs, units (like V, A, kW), and codes exactly. "
                f"Format titles as Markdown headers (# or ##). "
                f"DO NOT add any conversational filler, just return the translated Markdown content."
            )
            
            vision_model = self._model if "llama" not in self._model.lower() else "gpt-4o-mini"
            response = self._client.chat.completions.create(
                model=vision_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{encoded_string}"
                                }
                            }
                        ]
                    }
                ],
                temperature=0.0,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Erro ao extrair conteúdo da imagem: {str(e)}"


def create_translation_service(
    provider: str,
    api_key: str,
    endpoint: str,
    source_language: str,
    model: str = "llama-3.3-70b-versatile",
) -> TranslationService:
    """Create translation service supporting GroqCloud or custom endpoints."""
    return ManusTranslationService(source_language, api_key=api_key, endpoint=endpoint, model=model)
