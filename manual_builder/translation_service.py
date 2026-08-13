"""Translation service utilizing Manus AI for both text and page image translation."""

from __future__ import annotations

import os
import re
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

    def extract_structured_content(
        self,
        source: Path,
        target_language: str,
        source_text: str = "",
    ) -> str:
        """Extract and translate content as structured Markdown (text/tables)."""


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
        """Return only final technical content, never model commentary or echoed source text.

        Alguns modelos devolvem uma explicação antes do resultado, como ``TEXT:`` seguido
        do texto original e um bloco ``Tradução:``. Esse formato é útil somente para a
        conversa, mas não pode chegar ao R Markdown. Quando há um rótulo de resultado,
        apenas o conteúdo posterior ao último rótulo é preservado; nos demais casos,
        linhas de raciocínio, rótulos e comentários conhecidos são descartados.
        """
        if not content:
            return ""

        cleaned = re.sub(
            r"<think(?:\s[^>]*)?>.*?</think>",
            "",
            content,
            flags=re.IGNORECASE | re.DOTALL,
        ).strip()
        cleaned = re.sub(
            r"^```(?:markdown|md|text)?\s*|\s*```$",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip()
        if not cleaned:
            return ""

        # Preferir explicitamente o bloco final de tradução/resultado quando o modelo
        # tiver retornado uma comparação entre fonte e destino.
        result_markers = list(
            re.finditer(
                r"(?im)^\s*(?:tradu[cç][aã]o|translation|conte[úu]do\s+traduzido|resultado\s+final)\s*:\s*",
                cleaned,
            )
        )
        if result_markers:
            final_block = cleaned[result_markers[-1].end():].strip()
            if final_block:
                cleaned = final_block

        blocked_line = re.compile(
            r"(?i)^\s*(?:"
            r"n[aã]o\s+h[aá]\s+necessidade\s+de\s+tradu[cç][aã]o|"
            r"o\s+texto\s+j[aá]\s+est[aá]|"
            r"(?:aqui\s+est[aá]|segue)\s+(?:a\s+)?tradu[cç][aã]o|"
            r"(?:texto|text|texto\s+original|original|source)\s*:|"
            r"(?:tradu[cç][aã]o|translation|conte[úu]do\s+traduzido|resultado\s+final)\s*:"
            r")"
        )
        retained_lines = [
            line.rstrip()
            for line in cleaned.splitlines()
            if not blocked_line.match(line)
        ]
        cleaned = "\n".join(retained_lines).strip()
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

    def _structured_source_completion(self, source_text: str, target_language: str) -> str:
        """Translate extracted HTML or PDF text into clean Markdown without sending an image."""
        if self._client is None or not source_text.strip():
            return ""

        lang_name = LANGUAGE_NAMES.get(target_language, target_language)
        prompt = (
            "Você é um editor de manuais técnicos industriais. Converta o conteúdo-fonte abaixo "
            f"integralmente para {lang_name}. Traduza TODOS os títulos, rótulos, descrições e valores "
            "textuais; preserve códigos, números, unidades e referências técnicas. Quando detectar dados "
            "de duas ou mais colunas, reconstrua-os como uma tabela Markdown. Preserve listas e a ordem "
            "do conteúdo. Use parágrafos curtos, listas Markdown para procedimentos ou avisos e tabelas "
            "Markdown para dados técnicos. Retorne APENAS o Markdown final, sem explicações, sem bloco "
            "de código e sem marcadores de raciocínio. Não escreva rótulos como `TEXT:`, `Texto original:`, "
            "`Tradução:` ou `Resultado:` e não repita o conteúdo de origem antes da versão final. Inicie "
            "diretamente pelo primeiro título, parágrafo, lista ou tabela do manual.\n\n"
            f"CONTEÚDO-FONTE EXTRAÍDO:\n{source_text[:18000]}"
        )
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=3000,
                timeout=25.0,
            )
            return self._clean_model_output(response.choices[0].message.content)
        except Exception:
            return ""

    def extract_page_outline_text(self, source: Path) -> str:
        """Read a visual PDF page when the original document has no selectable text.

        The response is intentionally a short factual transcription, not a full translation.
        It supplies real page content to the structure analyser without trying to recreate the
        page as R Markdown at this stage.
        """
        if self._client is None or not source.exists():
            return ""
        try:
            import base64

            with open(source, "rb") as image_file:
                encoded_image = base64.b64encode(image_file.read()).decode("utf-8")
            prompt = (
                "Leia esta página de um manual técnico industrial. Retorne SOMENTE uma transcrição "
                "concisa e factual do que realmente aparece: título visível, avisos, procedimentos, "
                "dados técnicos e rótulos importantes. Preserve códigos, números e unidades. Não "
                "invente conteúdo, não descreva a imagem e não acrescente comentários. Limite-se a "
                "aproximadamente 180 palavras."
            )
            return self._vision_completion(prompt, encoded_image, max_tokens=360)
        except Exception:
            return ""

    def extract_structured_content(
        self,
        source: Path,
        target_language: str,
        source_text: str = "",
    ) -> str:
        """Extract and translate content as structured Markdown using HTML source or AI Vision."""
        if source_text.strip():
            structured = self._structured_source_completion(source_text, target_language)
            if structured:
                return structured

        if self._client is None:
            return ""

        try:
            import base64
            with open(source, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode("utf-8")

            lang_name = LANGUAGE_NAMES.get(target_language, "Brazilian Portuguese")
            prompt = (
                "Você é um especialista em tradução de manuais técnicos industriais. "
                "Analise esta imagem de página de manual e extraia TODO o conteúdo textual e tabelas. "
                f"TRADUZA ABSOLUTAMENTE TODO O TEXTO para {lang_name}. "
                "Não mantenha palavras ou frases no idioma de origem; traduza títulos, cabeçalhos, rótulos, "
                "observações e células de tabela. Reconstrua todas as tabelas em Markdown limpo e legível. "
                "Mantenha códigos, unidades (V, A, kW, Hz) e referências técnicas exatas. Retorne apenas o "
                "conteúdo Markdown traduzido, sem introduções, comentários, texto-fonte ecoado, rótulos "
                "como `TEXT:` ou `Tradução:`, nem blocos <think>."
            )
            response_text = self._vision_completion(prompt, encoded_string, max_tokens=2800)
            return self._clean_model_output(response_text)
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
