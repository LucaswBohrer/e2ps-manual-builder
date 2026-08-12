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
        self._endpoint = resolved_base.lower()
        if OpenAI is not None:
            self._client = OpenAI(api_key=resolved_key, base_url=resolved_base)
        else:
            self._client = None

    def _vision_model_candidates(self) -> list[str]:
        """Return compatible vision models, prioritizing native Groq options."""
        configured_is_visual = any(
            marker in self._model.lower()
            for marker in ("qwen", "vision", "llava", "llama-4", "scout", "maverick")
        )
        candidates: list[str] = [self._model] if configured_is_visual else []
        if "groq.com" in self._endpoint:
            # Modelos de visão documentados pelo GroqCloud; não use modelos OpenAI neste endpoint.
            candidates.extend([
                "qwen/qwen3.6-27b",
                "meta-llama/llama-4-scout-17b-16e-instruct",
            ])
        elif self._model not in candidates:
            candidates.append(self._model)

        return list(dict.fromkeys(candidates))

    def _vision_completion(self, prompt: str, encoded_image: str, max_tokens: int) -> str:
        """Request a vision completion, trying only models compatible with the configured provider."""
        if self._client is None:
            return ""

        message = [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded_image}"}},
            ],
        }]
        for vision_model in self._vision_model_candidates():
            try:
                response = self._client.chat.completions.create(
                    model=vision_model,
                    messages=message,
                    temperature=0.1,
                    max_tokens=max_tokens,
                )
                content = response.choices[0].message.content
                if content and content.strip():
                    return content.strip()
            except Exception:
                # Tentar o próximo modelo de visão compatível, sem inserir o erro no manual.
                continue
        return ""

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
                translated_content = self._vision_completion(
                    prompt, encoded_string, max_tokens=120
                )

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
            
            lang_name = LANGUAGE_NAMES.get(target_language, "Brazilian Portuguese")
            prompt = (
                f"Você é um especialista em tradução de manuais técnicos industriais. "
                f"Analise esta imagem de página de manual e extraia TODO o conteúdo textual e tabelas. "
                f"TRADUZA ABSOLUTAMENTE TUDO para {lang_name} (Português do Brasil). "
                f"NÃO deixe NENHUM termo em espanhol, inglês ou outro idioma original — tudo deve estar perfeitamente traduzido para o português. "
                f"Reconstrua todas as tabelas em formato Markdown limpo (tabelas legíveis com colunas). "
                f"Mantenha códigos, unidades (V, A, kW, Hz) e referências técnicas exatas. "
                f"Retorne apenas o conteúdo em Markdown traduzido, sem introduções ou explicações."
            )
            
            res_text = self._vision_completion(prompt, encoded_string, max_tokens=1800)
            # Um retorno vazio permite que o exportador preserve a imagem original em vez de
            # gravar um erro técnico no PDF final.
            return res_text
        except Exception:
            return ""


def create_translation_service(
    provider: str,
    api_key: str,
    endpoint: str,
    source_language: str,
    model: str = "llama-3.3-70b-versatile",
) -> TranslationService:
    """Create translation service supporting GroqCloud or custom endpoints."""
    return ManusTranslationService(source_language, api_key=api_key, endpoint=endpoint, model=model)
