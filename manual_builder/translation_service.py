"""Translation service utilizing Manus AI for both text and page image translation."""

from __future__ import annotations

import base64
import io
import os
import re
import time
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
        self._last_error = ""
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

    @property
    def last_error(self) -> str:
        """Return the last recoverable provider failure for a user-facing export message."""
        return self._last_error

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

    def _completion_with_retries(
        self,
        *,
        model: str,
        messages: list[dict],
        max_tokens: int,
        attempts: int = 2,
    ) -> str:
        """Request a completion with a bounded retry for transient Groq limits/timeouts."""
        if self._client is None:
            return ""

        self._last_error = ""
        for attempt in range(attempts):
            try:
                response = self._client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=max_tokens,
                    timeout=35.0,
                )
                content = self._clean_model_output(response.choices[0].message.content)
                if content:
                    return content
                self._last_error = "A IA retornou uma resposta vazia."
            except Exception as error:
                self._last_error = str(error)
                # TPM/429 e instabilidades momentâneas são comuns em planos gratuitos.
                # Uma espera curta permite que a página seja recuperada sem rebaixá-la a imagem.
                if attempt + 1 < attempts:
                    time.sleep(4.0)
        return ""

    @staticmethod
    def _encode_image_for_vision(source: Path) -> str:
        """Encode a readable but bounded page image for Groq Vision.

        Rendered PDF pages can be unnecessarily large.  Downscaling them before base64 encoding
        prevents an otherwise readable page from being rejected because the image request exceeds
        the provider's input/token allowance.
        """
        if Image is None:
            return base64.b64encode(source.read_bytes()).decode("utf-8")

        with Image.open(source) as opened:
            image = opened.convert("RGB")
            image.thumbnail((1500, 2100))
            buffer = io.BytesIO()
            image.save(buffer, format="PNG", optimize=True)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    def _vision_completion(self, prompt: str, encoded_image: str, max_tokens: int) -> str:
        """Request a vision completion, retrying compatible models before reporting failure."""
        if self._client is None:
            return ""

        message = [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded_image}"}},
            ],
        }]
        errors: list[str] = []
        for vision_model in self._vision_model_candidates():
            content = self._completion_with_retries(
                model=vision_model,
                messages=message,
                max_tokens=max_tokens,
                attempts=2,
            )
            if content:
                return content
            if self._last_error:
                errors.append(self._last_error)
        self._last_error = " | ".join(dict.fromkeys(errors))
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

    @staticmethod
    def _source_text_chunks(source_text: str, maximum_characters: int = 4200) -> list[str]:
        """Split dense extracted pages on line boundaries before an AI translation request.

        A page with tables can contain enough extracted characters to exceed Groq's per-request
        token window when combined with the requested Markdown output.  Smaller independent
        blocks keep the request reliable and are reassembled in the original reading order.
        """
        lines = [line.rstrip() for line in (source_text or "").splitlines()]
        chunks: list[str] = []
        current: list[str] = []
        current_length = 0
        for line in lines:
            line_length = len(line) + 1
            if current and current_length + line_length > maximum_characters:
                chunks.append("\n".join(current).strip())
                current = []
                current_length = 0
            if line_length > maximum_characters:
                for start in range(0, len(line), maximum_characters):
                    if current:
                        chunks.append("\n".join(current).strip())
                        current = []
                        current_length = 0
                    chunks.append(line[start:start + maximum_characters].strip())
                continue
            current.append(line)
            current_length += line_length
        if current:
            chunks.append("\n".join(current).strip())
        return [chunk for chunk in chunks if chunk]

    def _structured_source_completion(self, source_text: str, target_language: str) -> str:
        """Translate extracted HTML or PDF text into clean Markdown without sending an image."""
        if self._client is None or not source_text.strip():
            return ""

        lang_name = LANGUAGE_NAMES.get(target_language, target_language)
        translated_chunks: list[str] = []
        for source_chunk in self._source_text_chunks(source_text):
            prompt = (
                "Você é um editor de manuais técnicos industriais. Converta o conteúdo-fonte abaixo "
                f"integralmente para {lang_name}. Traduza TODOS os títulos, rótulos, descrições e valores "
                "textuais; preserve códigos, números, unidades e referências técnicas. Quando detectar dados "
                "de duas ou mais colunas, reconstrua-os como uma tabela Markdown. Preserve listas e a ordem "
                "do conteúdo. Use parágrafos curtos, listas Markdown para procedimentos ou avisos e tabelas "
                "Markdown para dados técnicos. Crie cabeçalhos Markdown SOMENTE quando o título estiver "
                "literalmente visível no conteúdo-fonte; não invente seções como Introdução, Conclusão, "
                "Descrição do produto ou Contato. Ignore números de página, rodapés, endereços, nomes da "
                "empresa e linhas de contato. Retorne APENAS o Markdown final, sem explicações, sem bloco "
                "de código e sem marcadores de raciocínio. Não escreva rótulos como `TEXT:`, `Texto original:`, "
                "`Tradução:` ou `Resultado:` e não repita o conteúdo de origem antes da versão final. Inicie "
                "diretamente pelo primeiro título, parágrafo, lista ou tabela do manual.\n\n"
                f"CONTEÚDO-FONTE EXTRAÍDO:\n{source_chunk}"
            )
            try:
                translated = self._completion_with_retries(
                    model=self._model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=1400,
                    attempts=2,
                )
                if translated:
                    translated_chunks.append(translated)
            except Exception as error:
                self._last_error = str(error)
                continue
        return "\n\n".join(translated_chunks).strip()

    @staticmethod
    def _requires_visual_layout_reconstruction(source_text: str) -> bool:
        """Detect PDF extraction symptoms that cannot safely become linear Markdown.

        PDF text extraction can preserve words while losing columns, callout boxes and reading
        order. In these cases the page image is a more reliable source for the final manual.
        """
        text = source_text or ""
        if not text.strip():
            return True
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if any(line.count("|") >= 6 for line in lines):
            return True
        if re.search(r"(?i)\b([\wÀ-ÿ]{3,})\s+\1\s+\1\b", text):
            return True
        for index in range(len(lines) - 2):
            if lines[index] == lines[index + 1] == lines[index + 2] and len(lines[index]) >= 3:
                return True
        return False

    def extract_page_outline_text(self, source: Path) -> str:
        """Read a visual PDF page when the original document has no selectable text.

        The response is intentionally a short factual transcription, not a full translation.
        It supplies real page content to the structure analyser without trying to recreate the
        page as R Markdown at this stage.
        """
        if self._client is None or not source.exists():
            return ""
        try:
            encoded_image = self._encode_image_for_vision(source)
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
        # A página só deve ir para leitura visual quando não houver texto extraível. Mesmo que
        # o texto venha de uma tabela ou de colunas, o modo Texto/Tabela precisa tentar a
        # reconstrução traduzida primeiro; preservar a página inteira em inglês é o último recurso.
        if source_text.strip():
            structured = self._structured_source_completion(source_text, target_language)
            if structured:
                return structured

        if self._client is None:
            return ""

        try:
            encoded_string = self._encode_image_for_vision(source)

            lang_name = LANGUAGE_NAMES.get(target_language, "Brazilian Portuguese")
            prompt = (
                "Você é um editor de manuais técnicos industriais e deve RECONSTRUIR o layout desta única "
                "página, não apenas transcrever palavras em ordem visual. Extraia todo o conteúdo útil e "
                f"TRADUZA ABSOLUTAMENTE TODO O TEXTO para {lang_name}. "
                "Mantenha códigos, números, unidades (V, A, kW, Hz) e referências técnicas exatas. "
                "Aplique obrigatoriamente estas regras: "
                "(1) ignore rodapés, números de página, logotipos e o número/título do capítulo quando ele "
                "apenas repete a seção principal; "
                "(2) cada cabeçalho deve ocupar sua própria linha Markdown e procedimentos devem usar listas "
                "numeradas ou marcadores; "
                "(3) se uma caixa de aviso, coluna ou painel repetir visualmente palavras como 'Etapa', "
                "'Sempre', 'Atenção' ou 'Perigo', escreva cada instrução apenas uma vez, no sentido lógico; "
                "(4) reconstrua tabelas em linhas Markdown completas, com cabeçalho, separador e uma linha por "
                "registro, jamais em uma única linha; "
                "(5) não invente nem resuma instruções técnicas; só crie títulos que estejam visíveis na página "
                "e ignore rodapés, endereços e contatos; "
                "(6) se a página for predominantemente um desenho técnico, diagrama, vista explodida, fotografia "
                "ou painel de símbolos sem procedimento, tabela ou texto explicativo suficiente, retorne "
                "EXATAMENTE [[KEEP_AS_IMAGE]] e nada mais. "
                "Retorne somente o Markdown final, sem explicações, comentários, texto-fonte ecoado, rótulos "
                "como `TEXT:` ou `Tradução:`, nem blocos <think>."
            )
            response_text = self._vision_completion(prompt, encoded_string, max_tokens=2200)
            structured = self._clean_model_output(response_text)
            if structured:
                return structured
            # If visual reading is temporarily unavailable, preserve the text path rather
            # than silently losing the page. The exporter can still fall back to its image.
            if source_text.strip():
                return self._structured_source_completion(source_text, target_language)
            return ""
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
