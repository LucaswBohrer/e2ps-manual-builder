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
            # Limita cada solicitação remota para que uma falha/problema no provedor
            # não mantenha o trabalhador de exportação bloqueado indefinidamente.
            self._client = OpenAI(
                api_key=resolved_key,
                base_url=resolved_base,
                timeout=25.0,
                max_retries=0,
            )
        else:
            self._client = None

    def _vision_model_candidates(self) -> list[str]:
        """Return compatible vision models, prioritizing native Groq options."""
        configured_is_visual = any(
            marker in self._model.lower()
            for marker in ("qwen", "vision", "llava", "llama-4", "scout", "maverick")
        )
        candidates: list[str] = []
        if "groq.com" in self._endpoint:
            # Priorizar Llama 4 Scout: o modelo retorna uma resposta final direta.
            # Qwen fica somente como alternativa, pois pode emitir blocos <think>.
            candidates.extend([
                "meta-llama/llama-4-scout-17b-16e-instruct",
                "qwen/qwen3.6-27b",
            ])
            if configured_is_visual:
                candidates.append(self._model)
        else:
            candidates.append(self._model)

        return list(dict.fromkeys(candidates))

    @staticmethod
    def _clean_model_output(content: str | None) -> str:
        """Discard hidden reasoning and return only safe user-facing model text."""
        if not content:
            return ""
        cleaned = content.strip()
        # Modelos de raciocínio podem devolver o pensamento interno em `content`.
        # Esse material nunca pode ir para o PDF nem ser desenhado em uma imagem.
        if "<think" in cleaned.lower() or "</think>" in cleaned.lower():
            return ""
        return cleaned

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
                    timeout=25.0,
                )
                content = self._clean_model_output(response.choices[0].message.content)
                if content:
                    return content
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
            return self._clean_model_output(response.choices[0].message.content) or text
        except Exception:
            return text

    def translate_page(self, source: Path, target: Path, target_language: str) -> None:
        """Preserve a page image without adding unreliable AI text overlays.

        Groq Vision can read an image, but it does not create a replacement image with
        translated typography at the original positions. The reliable translated output
        is therefore generated by ``extract_structured_content`` in Text/Table mode.
        """
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
                f"TRADUZA ABSOLUTAMENTE TODO O TEXTO para {lang_name}. "
                f"Não mantenha palavras ou frases no idioma de origem; traduza títulos, cabeçalhos, rótulos, observações e células de tabela. "
                f"Reconstrua todas as tabelas em formato Markdown limpo (tabelas legíveis com colunas). "
                f"Mantenha códigos, unidades (V, A, kW, Hz) e referências técnicas exatas. "
                f"Retorne apenas o conteúdo em Markdown traduzido, sem introduções, comentários, marcadores de raciocínio ou blocos <think>."
            )
            
            res_text = self._vision_completion(prompt, encoded_string, max_tokens=1800)
            # Um retorno vazio permite que o exportador preserve a imagem original em vez de
            # gravar um erro técnico no PDF final.
            return self._clean_model_output(res_text)
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
