"""AI assistant service for automated manual structuring and technical text generation with real PDF text context."""

from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from manual_builder.models import PdfPage


@dataclass(slots=True)
class PdfStructureSubsection:
    """A selected subset of PDF pages that forms an editable manual subsection."""

    title: str
    page_numbers: list[int] = field(default_factory=list)
    intro: str = ""
    evidence: str = ""


@dataclass(slots=True)
class PdfStructureSection:
    """A selected subset of PDF pages that forms an editable manual section."""

    title: str
    page_numbers: list[int] = field(default_factory=list)
    intro: str = ""
    evidence: str = ""
    subsections: list[PdfStructureSubsection] = field(default_factory=list)


@dataclass(slots=True)
class PdfStructurePlan:
    """Compact, editable E2PS outline inferred from a manufacturer PDF."""

    document_title: str = ""
    sections: list[PdfStructureSection] = field(default_factory=list)
    selected_page_numbers: list[int] = field(default_factory=list)
    omitted_page_numbers: list[int] = field(default_factory=list)
    used_ai: bool = False
    note: str = ""
    extracted_text_by_page: dict[int, str] = field(default_factory=dict)
    detected_chapter_ranges: dict[str, list[int]] = field(default_factory=dict)
    coverage_warnings: list[str] = field(default_factory=list)


class ManualAIService:
    """Service utilizing custom OpenAI-compatible API (like Groq) with real PDF content analysis."""

    def __init__(self, api_key: str = "", base_url: str = "", model: str = "gpt-4o-mini") -> None:
        self.update_key(api_key, base_url, model)
        self._chat_history = [
            {"role": "system", "content": "You are a professional technical documentation assistant for E2PS manuals. You analyze real extracted text from PDF pages, help the user structure manuals logically, choose which pages belong to which sections, and write professional technical descriptions in Portuguese."}
        ]

    def update_key(self, api_key: str, base_url: str = "", model: str = "gpt-4o-mini") -> None:
        """Update API client with new key, base url and model."""
        key = api_key.strip()
        url = base_url.strip() or "https://api.openai.com/v1"
        self._model = model.strip() or "gpt-4o-mini"
        
        if OpenAI is not None and key and key != "sandbox-key":
            try:
                self._client = OpenAI(api_key=key, base_url=url)
            except Exception:
                self._client = None
        else:
            self._client = None

    def test_connection(self) -> tuple[bool, str]:
        """Test API connection with a minimal request."""
        if self._client is None:
            return False, "Cliente IA não inicializado (Verifique se preencheu a API Key)."
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            return True, f"Conexão bem-sucedida com o modelo '{self._model}'!"
        except Exception as error:
            return False, f"Falha na conexão: {error}"

    def ask_ai(self, user_message: str, pages_summary: str = "") -> str:
        """Chat with the AI assistant, incorporating concise page text context."""
        if self._client is None:
            return (
                f"[Modo Auxiliar Inteligente (Sem Chave API configurada ou cliente inativo)]\n"
                f"Sua pergunta: '{user_message}'.\n"
                f"Resumo do PDF: {pages_summary}\n"
                f"Dica: Configure sua API Key e URL base (ex: Groq) no painel superior para interagir com a IA real."
            )

        # Keep chat history bounded (system prompt + last 6 messages max) to avoid TPM limits
        if len(self._chat_history) > 7:
            self._chat_history = [self._chat_history[0]] + self._chat_history[-6:]

        # Truncate pages_summary if too large
        trimmed_summary = pages_summary[:1000] if len(pages_summary) > 1000 else pages_summary
        context_msg = f"Contexto do PDF (resumido): {trimmed_summary}\n\nPergunta do usuário: {user_message}"
        
        messages = self._chat_history + [{"role": "user", "content": context_msg}]

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=0.3,
                max_tokens=800,
            )
            reply = response.choices[0].message.content.strip()
            self._chat_history.append({"role": "user", "content": context_msg})
            self._chat_history.append({"role": "assistant", "content": reply})
            return reply
        except Exception as error:
            return f"Erro ao comunicar com a IA ({self._model} @ {self._client.base_url if hasattr(self._client, 'base_url') else 'API'}): {error}"

    def suggest_structure_text(self, pages: list[PdfPage], manual_title: str) -> str:
        """Return an auditable selection summary instead of an ungrounded free-form outline."""
        plan = self.create_pdf_structure(pages, manual_title)
        if not plan.sections:
            return plan.note or "Não foi possível encontrar conteúdo técnico suficiente no PDF."
        lines = [plan.note] if plan.note else []
        for section in plan.sections:
            page_list = ", ".join(str(number) for number in section.page_numbers)
            evidence = f" Evidência: “{section.evidence}”." if section.evidence else ""
            lines.append(f"{section.title} — páginas {page_list}.{evidence}")
            for subsection in section.subsections:
                sub_pages = ", ".join(str(number) for number in subsection.page_numbers)
                sub_evidence = (
                    f" Evidência: “{subsection.evidence}”." if subsection.evidence else ""
                )
                lines.append(f"  - {subsection.title} — páginas {sub_pages}.{sub_evidence}")
        return "\n".join(lines)

    _SOURCE_CHAPTERS: tuple[tuple[int, str, tuple[str, ...]], ...] = (
        (1, "Informações gerais", ("general information", "introduction", "informações gerais", "informacion general")),
        (2, "Segurança", ("safety", "segurança", "seguridad")),
        (3, "Instalação", ("installation", "instalação", "instalacion")),
        (4, "Operação", ("operation", "operação", "operacion")),
        (5, "Manutenção", ("maintenance", "manutenção", "mantenimiento")),
        (6, "Dados técnicos", ("technical data", "dados técnicos", "datos técnicos")),
        (7, "Peças e kits de serviço", ("parts list and service kits", "service kits", "lista de peças", "lista de piezas")),
    )
    _ESSENTIAL_CHAPTER_NUMBERS = frozenset({2, 3, 4, 5, 6, 7})
    _SUBSECTION_TITLES = {
        "important information": "Informações importantes",
        "warning signs": "Sinais de advertência",
        "safety precautions": "Precauções de segurança",
        "unpacking/delivery": "Desembalagem e entrega",
        "unpacking delivery": "Desembalagem e entrega",
        "installation": "Instalação",
        "pre-use check - pump without impeller screw": "Verificação antes do uso — bomba sem parafuso do impulsor",
        "pre-use check - pump with impeller screw": "Verificação antes do uso — bomba com parafuso do impulsor",
        "recycling information": "Informações de reciclagem",
        "operation/control": "Operação e controle",
        "controls": "Controles",
        "trouble shooting": "Solução de problemas",
        "troubleshooting": "Solução de problemas",
        "recommended cleaning": "Limpeza recomendada",
        "general maintenance": "Manutenção geral",
        "cleaning procedure": "Procedimento de limpeza",
        "dismantling of pump/shaft seals": "Desmontagem da bomba e das vedações do eixo",
        "assembly of pump/single shaft seal": "Montagem da bomba com vedação simples do eixo",
        "assembly of pump/flushed shaft seal": "Montagem da bomba com vedação do eixo lavada",
        "assembly of pump/double mechanical shaft seal": "Montagem da bomba com vedação mecânica dupla",
        "adjustment of shaft (lkh-5)": "Ajuste do eixo (LKH-5)",
        "adjustment of shaft (lkh-10 to -90)": "Ajuste do eixo (LKH-10 a -90)",
        "motor maintenance": "Manutenção do motor",
        "technical data": "Dados técnicos",
        "relubrication intervals": "Intervalos de relubrificação",
        "torque specifications": "Especificações de torque",
        "materials": "Materiais",
        "weight": "Peso",
        "weight (kg)": "Peso (kg)",
        "noise": "Ruído",
        "noise emission": "Emissão de ruído",
        "lkh-5 sanitary version": "LKH-5 — versão sanitária",
        "lkh-10, -15, -20, -25, -35, -40, -50, -60, -70, -75, -85, -90 sanitary version": "LKH-10 a -90 — versão sanitária",
        "lkh - product wetted parts": "LKH — peças em contato com o produto",
        "lkh - motor-dependent parts": "LKH — peças dependentes do motor",
        "lkh - shaft seal": "LKH — vedação do eixo",
    }

    @staticmethod
    def _normalised_heading(value: str) -> str:
        """Normalize a source heading without losing the original text used as evidence."""
        return re.sub(r"\s+", " ", value or "").strip(" .:;-–—").lower()

    @classmethod
    def _chapter_heading_on_page(cls, page: PdfPage) -> tuple[int, str] | None:
        """Recognize a manufacturer chapter heading near the beginning of a page.

        PyMuPDF commonly returns the chapter number and its title in separate lines, so
        both ``2 Safety`` and the two-line form ``2`` / ``Safety`` are supported.
        The small window prevents a reference to another chapter in the body text from
        becoming a false chapter boundary.
        """
        lines = [
            re.sub(r"\s+", " ", raw_line).strip(" .:;-–—")
            for raw_line in page.analysis_text.splitlines()[:14]
        ]
        lines = [line for line in lines if line]
        for index, line in enumerate(lines):
            match = re.fullmatch(r"(\d{1,2})(?:\s+(.{3,100}))?", line)
            if not match:
                continue
            number = int(match.group(1))
            candidate = match.group(2) or (lines[index + 1] if index + 1 < len(lines) else "")
            heading = cls._normalised_heading(candidate)
            for chapter_number, title, aliases in cls._SOURCE_CHAPTERS:
                if number == chapter_number and any(
                    heading == alias or heading.startswith(f"{alias} ") for alias in aliases
                ):
                    return chapter_number, title
        return None

    @classmethod
    def _subsection_heading_on_page(
        cls, page: PdfPage, chapter_number: int
    ) -> str | None:
        """Recognize a numbered subsection title and translate known technical labels."""
        lines = [
            re.sub(r"\s+", " ", raw_line).strip(" .:;-–—")
            for raw_line in page.analysis_text.splitlines()[:42]
        ]
        lines = [line for line in lines if line]
        for index, line in enumerate(lines):
            match = re.fullmatch(r"(\d{1,2})\.(\d{1,2})(?:\.\d+)?(?:\s+(.{3,100}))?", line)
            if not match or int(match.group(1)) != chapter_number:
                continue
            raw_title = re.sub(
                r"\s+", " ", match.group(3) or (lines[index + 1] if index + 1 < len(lines) else "")
            ).strip()
            if not raw_title:
                continue
            normalized = cls._normalised_heading(raw_title)
            return cls._SUBSECTION_TITLES.get(normalized, raw_title)
        return None

    @staticmethod
    def _is_non_operational_page(page: PdfPage) -> bool:
        """Exclude only clear front-matter/legal pages from source-driven coverage."""
        text = re.sub(r"\s+", " ", page.analysis_text).lower()
        excluded_terms = (
            "table of contents", "copyright", "all rights reserved", "declaration of conformity",
            "declaration of incorporation", "certificate of conformity", "revision history",
        )
        return any(term in text for term in excluded_terms)

    def _source_heading_structure(
        self, pages: list[PdfPage], manual_title: str
    ) -> PdfStructurePlan:
        """Build an auditable, complete outline from chapter and subsection boundaries.

        This path is intentionally deterministic.  When a manufacturer PDF supplies reliable
        numbered headings, those headings are stronger evidence than a model choosing a single
        representative page.  Each detected chapter keeps its full continuous page interval,
        while numbered subsections split that interval into editable groups.
        """
        ordered_pages = sorted(pages, key=lambda page: page.number)
        chapter_starts: list[tuple[int, int, str]] = []
        for index, page in enumerate(ordered_pages):
            if self._is_non_operational_page(page):
                continue
            heading = self._chapter_heading_on_page(page)
            if heading is None:
                continue
            number, title = heading
            if not chapter_starts or chapter_starts[-1][1] != number:
                chapter_starts.append((index, number, title))

        if not chapter_starts:
            return PdfStructurePlan(document_title=manual_title.strip())

        sections: list[PdfStructureSection] = []
        selected: list[int] = []
        detected_ranges: dict[str, list[int]] = {}
        for chapter_index, (start_index, chapter_number, chapter_title) in enumerate(chapter_starts):
            end_index = (
                chapter_starts[chapter_index + 1][0]
                if chapter_index + 1 < len(chapter_starts)
                else len(ordered_pages)
            )
            chapter_pages = [
                page for page in ordered_pages[start_index:end_index]
                if page.analysis_text.strip() and not self._is_non_operational_page(page)
            ]
            if not chapter_pages:
                continue

            subsection_starts: list[tuple[int, str]] = []
            for relative_index, page in enumerate(chapter_pages):
                subsection_title = self._subsection_heading_on_page(page, chapter_number)
                if subsection_title and (
                    not subsection_starts or subsection_starts[-1][1] != subsection_title
                ):
                    subsection_starts.append((relative_index, subsection_title))

            direct_pages = chapter_pages[: subsection_starts[0][0]] if subsection_starts else chapter_pages
            subsections: list[PdfStructureSubsection] = []
            for subsection_index, (sub_start, subsection_title) in enumerate(subsection_starts):
                sub_end = (
                    subsection_starts[subsection_index + 1][0]
                    if subsection_index + 1 < len(subsection_starts)
                    else len(chapter_pages)
                )
                subsection_pages = chapter_pages[sub_start:sub_end]
                numbers = [page.number for page in subsection_pages]
                if not numbers:
                    continue
                subsections.append(
                    PdfStructureSubsection(
                        title=subsection_title,
                        page_numbers=numbers,
                        intro="",
                        evidence=self._local_page_evidence(numbers, ordered_pages),
                    )
                )

            direct_numbers = [page.number for page in direct_pages]
            all_numbers = [page.number for page in chapter_pages]
            if chapter_number not in self._ESSENTIAL_CHAPTER_NUMBERS:
                continue
            selected.extend(all_numbers)
            detected_ranges[chapter_title] = all_numbers
            sections.append(
                PdfStructureSection(
                    title=chapter_title,
                    page_numbers=direct_numbers,
                    intro="",
                    evidence=self._local_page_evidence(direct_numbers or all_numbers, ordered_pages),
                    subsections=subsections,
                )
            )

        available = {page.number for page in ordered_pages}
        selected = sorted(dict.fromkeys(selected))
        return PdfStructurePlan(
            document_title=manual_title.strip(),
            sections=sections,
            selected_page_numbers=selected,
            omitted_page_numbers=sorted(available - set(selected)),
            detected_chapter_ranges=detected_ranges,
            note=(
                "Estrutura de cobertura criada a partir dos capítulos e subtítulos numerados "
                "detectados no PDF. Cada capítulo manteve o intervalo contínuo de páginas entre "
                "seu título e o próximo capítulo."
            ) if sections else "",
        )

    def create_pdf_structure(self, pages: list[PdfPage], manual_title: str) -> PdfStructurePlan:
        """Create a compact E2PS outline, selecting only useful manufacturer-PDF content.

        The model receives bounded, page-numbered extracted text and is explicitly instructed to
        discard commercial, legal and duplicate material. When an API is unavailable or responds
        with malformed data, a conservative local classification still produces an editable plan.
        """
        source_pages = sorted(
            (page for page in pages if page.variant == 1 and page.source_type == "pdf"),
            key=lambda page: page.number,
        )
        if not source_pages:
            return PdfStructurePlan(
                document_title=manual_title.strip(),
                note="Não há páginas de PDF disponíveis para análise automática.",
            )

        source_outline = self._source_heading_structure(source_pages, manual_title)
        if source_outline.sections:
            return source_outline

        fallback = self._fallback_pdf_structure(source_pages, manual_title)
        if not fallback.sections:
            return PdfStructurePlan(
                document_title=manual_title.strip(),
                note=(
                    "O PDF não forneceu texto técnico suficiente para selecionar páginas. "
                    "Se ele for escaneado, a leitura visual da IA precisa estar configurada; "
                    "caso contrário, importe imagens ou adicione páginas manualmente."
                ),
            )
        if self._client is None:
            fallback.note = (
                "Estrutura inicial criada a partir do texto extraído do PDF. Configure a IA para "
                "refinar a seleção do conteúdo essencial."
            )
            return fallback

        context = self._pdf_page_context(source_pages)
        prompt = (
            "Você é um especialista em documentação técnica industrial da E2PS. A partir das páginas "
            "extraídas abaixo, crie SOMENTE o conteúdo essencial para um manual E2PS enxuto. Não copie "
            "nem organize todo o manual do fabricante. Descarte capa, índice, marketing, certificados, "
            "declarações legais, revisões, páginas repetidas e material de referência não operacional. "
            "Priorize segurança, instalação/comissionamento, operação, manutenção/diagnóstico e dados "
            "técnicos indispensáveis. Se uma categoria não estiver presente, não a invente.\n\n"
            "Prefira retornar JSON válido, sem Markdown, neste formato:\n"
            '{"document_title":"...","sections":[{"title":"...","intro":"máximo duas frases em português","evidence":"trecho literal de pelo menos 12 caracteres extraído de uma página selecionada","pages":[1],"subsections":[{"title":"...","intro":"...","evidence":"trecho literal da página","pages":[2]}]}]}\n\n'
            "Regras obrigatórias: no máximo 8 seções; cada página aparece no máximo uma vez; escolha "
            "apenas páginas realmente necessárias; use somente números das páginas fornecidas; cada grupo "
            "com páginas deve conter evidence, uma citação literal verificável de uma das suas próprias "
            "páginas. Não use títulos genéricos como Introdução, Descrição Técnica ou Referências se não "
            "houver evidência explícita. Textos de introdução não podem criar especificações não existentes. "
            "Se não conseguir retornar JSON, responda somente com uma lista estruturada: `1. Título — páginas 3-4`, "
            "uma seção por linha, usando exclusivamente páginas fornecidas.\n\n"
            f"Título informado: {manual_title or 'Manual técnico'}\n\nPáginas extraídas:\n{context}"
        )
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "system",
                        "content": "Prefer strict JSON only. If JSON is unavailable, return only a numbered outline with exact page numbers and no commentary.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=1800,
            )
            raw = response.choices[0].message.content or ""
            plan = self._parse_pdf_structure(raw, source_pages, manual_title)
            if plan.sections:
                plan.used_ai = True
                plan.note = "Estrutura enxuta criada pela IA a partir do conteúdo extraído do PDF."
                return plan
        except Exception as error:
            fallback.note = (
                "A IA não pôde concluir a análise; foi criada uma seleção local editável. "
                f"Detalhe: {error}"
            )
            return fallback

        fallback.note = (
            "A IA não retornou uma estrutura utilizável; a estrutura editável foi criada diretamente "
            "a partir do conteúdo técnico detectado nas páginas do PDF."
        )
        return fallback

    @staticmethod
    def _clean_model_output(value: str) -> str:
        """Strip common reasoning wrappers and Markdown fences before JSON decoding."""
        cleaned = re.sub(
            r"<think(?:\s[^>]*)?>.*?</think>", "", value, flags=re.IGNORECASE | re.DOTALL
        ).strip()
        incomplete_reasoning = re.search(r"<think(?:\s[^>]*)?>", cleaned, flags=re.IGNORECASE)
        if incomplete_reasoning:
            cleaned = cleaned[:incomplete_reasoning.start()].strip()
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE).strip()
        start, end = cleaned.find("{"), cleaned.rfind("}")
        return cleaned[start:end + 1] if start >= 0 and end >= start else cleaned

    @staticmethod
    def _compact_text(value: object, limit: int = 360) -> str:
        text = re.sub(r"\s+", " ", str(value or "")).strip()
        return text[:limit].rstrip()

    def _pdf_page_context(self, pages: list[PdfPage]) -> str:
        """Build a bounded, numbered context with enough literal text for evidence checking."""
        snippets: list[str] = []
        for page in pages[:60]:
            excerpt = self._compact_text(page.analysis_text, 420)
            if excerpt:
                snippets.append(f"PÁGINA {page.number}: {excerpt}")
        context = "\n".join(snippets)
        return context[:18000]

    @staticmethod
    def _evidence_matches_pages(evidence: str, page_numbers: list[int], page_texts: dict[int, str]) -> bool:
        """Require a cited fragment to be materially present in at least one selected page."""
        normalized_evidence = re.sub(r"\s+", " ", evidence.lower()).strip()
        if len(normalized_evidence) < 12:
            return False
        evidence_tokens = set(re.findall(r"[a-zà-ÿ0-9]{4,}", normalized_evidence))
        if len(evidence_tokens) < 2:
            return False
        for page_number in page_numbers:
            page_text = page_texts.get(page_number, "")
            if normalized_evidence in page_text:
                return True
            page_tokens = set(re.findall(r"[a-zà-ÿ0-9]{4,}", page_text))
            overlap = len(evidence_tokens & page_tokens)
            if overlap >= 3 and overlap / len(evidence_tokens) >= 0.70:
                return True
        return False

    def _parse_pdf_structure(
        self,
        raw: str,
        pages: list[PdfPage],
        manual_title: str,
    ) -> PdfStructurePlan:
        """Validate model JSON and convert it to a safe, de-duplicated page plan."""
        try:
            payload = json.loads(self._clean_model_output(raw))
        except (TypeError, json.JSONDecodeError):
            return self._parse_pdf_structure_text(raw, pages, manual_title)
        return self._parse_pdf_payload(payload, pages, manual_title)

    def _parse_pdf_payload(
        self,
        payload: object,
        pages: list[PdfPage],
        manual_title: str,
    ) -> PdfStructurePlan:
        """Validate a JSON payload and convert it to a safe, de-duplicated page plan."""
        available = {page.number for page in pages}
        page_texts = {
            page.number: re.sub(r"\s+", " ", page.analysis_text.lower()).strip()
            for page in pages
        }
        used: set[int] = set()
        sections: list[PdfStructureSection] = []
        raw_sections = payload.get("sections", []) if isinstance(payload, dict) else []
        if not isinstance(raw_sections, list):
            return PdfStructurePlan()

        for raw_section in raw_sections[:8]:
            if not isinstance(raw_section, dict):
                continue
            title = self._compact_text(raw_section.get("title"), 90)
            if not title:
                continue
            direct_pages = self._valid_unused_pages(raw_section.get("pages"), available, used)
            evidence = self._compact_text(raw_section.get("evidence"), 260)
            if direct_pages and not self._evidence_matches_pages(evidence, direct_pages, page_texts):
                for page_number in direct_pages:
                    used.discard(page_number)
                direct_pages = []
            subsections: list[PdfStructureSubsection] = []
            raw_subsections = raw_section.get("subsections", [])
            if isinstance(raw_subsections, list):
                for raw_subsection in raw_subsections[:8]:
                    if not isinstance(raw_subsection, dict):
                        continue
                    subsection_title = self._compact_text(raw_subsection.get("title"), 90)
                    subsection_pages = self._valid_unused_pages(
                        raw_subsection.get("pages"), available, used
                    )
                    subsection_evidence = self._compact_text(raw_subsection.get("evidence"), 260)
                    if subsection_pages and not self._evidence_matches_pages(
                        subsection_evidence, subsection_pages, page_texts
                    ):
                        for page_number in subsection_pages:
                            used.discard(page_number)
                        subsection_pages = []
                    if subsection_title and subsection_pages:
                        subsections.append(
                            PdfStructureSubsection(
                                title=subsection_title,
                                page_numbers=subsection_pages,
                                intro=self._source_backed_intro(
                                    raw_subsection.get("intro"), subsection_pages, pages
                                ),
                                evidence=subsection_evidence,
                            )
                        )
            if direct_pages or subsections:
                sections.append(
                    PdfStructureSection(
                        title=title,
                        page_numbers=direct_pages,
                        intro=self._source_backed_intro(
                            raw_section.get("intro"), direct_pages, pages
                        ),
                        evidence=evidence,
                        subsections=subsections,
                    )
                )

        selected = sorted(used)
        title = self._compact_text(
            payload.get("document_title") if isinstance(payload, dict) else manual_title,
            140,
        ) or manual_title.strip()
        return PdfStructurePlan(
            document_title=title,
            sections=sections,
            selected_page_numbers=selected,
            omitted_page_numbers=sorted(available - set(selected)),
        )

    @staticmethod
    def _page_numbers_from_text(value: str, available: set[int]) -> list[int]:
        """Read explicit page numbers and short numeric ranges from a textual outline."""
        selected: list[int] = []
        for start_text, end_text in re.findall(r"(\d+)(?:\s*[-–]\s*(\d+))?", value):
            start = int(start_text)
            end = int(end_text) if end_text else start
            if end < start or end - start > 40:
                end = start
            for page_number in range(start, end + 1):
                if page_number in available and page_number not in selected:
                    selected.append(page_number)
        return selected

    @staticmethod
    def _literal_evidence(page_numbers: list[int], page_texts: dict[int, str]) -> str:
        """Pick a visible text fragment from selected PDF pages for auditable fallback evidence."""
        for page_number in page_numbers:
            text = re.sub(r"\s+", " ", page_texts.get(page_number, "")).strip()
            if len(text) < 12:
                continue
            sentences = re.split(r"(?<=[.!?])\s+", text)
            for sentence in sentences:
                if len(sentence) >= 12 and len(re.findall(r"[a-zà-ÿ0-9]", sentence.lower())) >= 8:
                    return sentence[:240].rstrip()
            return text[:240].rstrip()
        return ""

    @staticmethod
    def _title_matches_pages(title: str, page_numbers: list[int], page_texts: dict[int, str]) -> bool:
        """Reject generic headings unless their topic is supported by the selected page text."""
        combined_text = " ".join(page_texts.get(number, "") for number in page_numbers).lower()
        normalized_title = re.sub(r"[^a-zà-ÿ0-9 ]", " ", title.lower())
        title_tokens = {
            token for token in re.findall(r"[a-zà-ÿ0-9]{4,}", normalized_title)
            if token not in {"manual", "técnico", "tecnica", "geral", "sistema", "seção", "secao"}
        }
        if title_tokens and any(token in combined_text for token in title_tokens):
            return True
        topic_terms = {
            "seguran": ("safety", "warning", "danger", "caution", "seguran", "aviso"),
            "instal": ("install", "mount", "wiring", "commission", "instal"),
            "opera": ("operation", "operat", "start", "control", "operaç"),
            "manuten": ("maintenance", "maintain", "service", "manuten"),
            "diagn": ("troubleshoot", "fault", "diagnostic", "erro", "falha"),
            "dados": ("technical data", "specification", "rating", "voltage", "current", "dados técnicos"),
        }
        return any(
            title_key in normalized_title and any(term in combined_text for term in required_terms)
            for title_key, required_terms in topic_terms.items()
        )

    def _parse_pdf_structure_text(
        self,
        raw: str,
        pages: list[PdfPage],
        manual_title: str,
    ) -> PdfStructurePlan:
        """Convert a numbered or Markdown outline into a verified PDF structure.

        Some providers answer in prose despite JSON instructions.  This parser only accepts lines
        that name existing pages, have a supported title and can be tied to literal page text.
        """
        available = {page.number for page in pages}
        page_texts = {
            page.number: re.sub(r"\s+", " ", page.analysis_text.lower()).strip()
            for page in pages
        }
        pattern = re.compile(
            r"(?im)^\s*(?:#{1,6}\s*|\d+[.)]\s*|[-*+]\s*)?"
            r"(?:\*\*)?\s*([^*\n(]{3,100}?)\s*(?:\*\*)?\s*"
            r"(?:[-–—:]\s*)?\(?\s*(?:p[aá]g\.?(?:ina|inas)?|pages?)\s*[:#]?\s*"
            r"([0-9][0-9, \t\-–]*)\)?",
        )
        matches = list(pattern.finditer(raw or ""))
        used: set[int] = set()
        sections: list[PdfStructureSection] = []
        for index, match in enumerate(matches[:12]):
            title = self._compact_text(re.sub(r"\s+", " ", match.group(1)), 90).strip(" -–—:.")
            candidate_pages = self._page_numbers_from_text(match.group(2), available)
            candidate_pages = [number for number in candidate_pages if number not in used]
            if not title or not candidate_pages or not self._title_matches_pages(title, candidate_pages, page_texts):
                continue
            detail_end = matches[index + 1].start() if index + 1 < len(matches) else len(raw)
            detail = raw[match.end():detail_end]
            evidence_match = re.search(
                r"(?:evid[eê]ncia|trecho|cita[cç][aã]o)\s*[:\-]\s*[\"“']?(.{12,260})",
                detail,
                flags=re.IGNORECASE | re.DOTALL,
            )
            evidence = self._compact_text(evidence_match.group(1), 240) if evidence_match else ""
            if not self._evidence_matches_pages(evidence, candidate_pages, page_texts):
                evidence = self._literal_evidence(candidate_pages, page_texts)
            if not self._evidence_matches_pages(evidence, candidate_pages, page_texts):
                continue
            used.update(candidate_pages)
            sections.append(
                PdfStructureSection(
                    title=title,
                    page_numbers=candidate_pages,
                    evidence=evidence,
                )
            )
        return PdfStructurePlan(
            document_title=manual_title.strip(),
            sections=sections,
            selected_page_numbers=sorted(used),
            omitted_page_numbers=sorted(available - used),
        )

    @staticmethod
    def _valid_unused_pages(value: object, available: set[int], used: set[int]) -> list[int]:
        """Keep only valid numeric page references and place each page once."""
        if not isinstance(value, list):
            return []
        selected: list[int] = []
        for page_number in value:
            try:
                normalized = int(page_number)
            except (TypeError, ValueError):
                continue
            if normalized in available and normalized not in used:
                used.add(normalized)
                selected.append(normalized)
        return selected

    def _fallback_pdf_structure(
        self, pages: list[PdfPage], manual_title: str
    ) -> PdfStructurePlan:
        """Create a conservative local selection when AI is unavailable.

        This deliberately limits the result instead of reproducing the manufacturer manual.
        """
        categories = [
            ("Segurança", ("safety", "segurança", "danger", "warning", "caution", "aviso")),
            ("Instalação e comissionamento", ("installation", "instala", "mounting", "wiring", "commission")),
            ("Operação", ("operation", "operaç", "operating", "uso", "start", "controle")),
            ("Dados técnicos", ("technical data", "dados técnicos", "specification", "rating", "tensão", "current")),
            ("Manutenção e diagnóstico", ("maintenance", "manuten", "troubleshoot", "falha", "fault", "diagnostic")),
        ]
        excluded_terms = (
            "table of contents", "índice", "copyright", "all rights reserved", "declaration",
            "certificate", "certificado", "revision history", "histórico de revisão",
        )
        total = len(pages)
        # A seleção local é uma sugestão editável, não um corte rígido de 60% do
        # documento. Um limite mais alto preserva páginas correlatas de segurança,
        # operação e manutenção que normalmente aparecem em sequência.
        selection_limit = min(total, max(10, min(36, math.ceil(total * 0.85))))
        buckets: dict[str, list[int]] = {title: [] for title, _terms in categories}
        remaining: list[int] = []
        last_category: str | None = None
        last_page_number: int | None = None

        for page in pages:
            text = self._compact_text(page.analysis_text, 900).lower()
            if not text or any(term in text for term in excluded_terms):
                last_category = None
                last_page_number = page.number
                continue

            # Uma página de manutenção contém frequentemente a palavra "operation".
            # Por isso escolhemos o tema com mais ocorrências, em vez da primeira
            # categoria que coincidir, evitando deslocar manutenção para Operação.
            scored_categories = [
                (sum(text.count(term) for term in terms), title)
                for title, terms in categories
            ]
            score, matched_title = max(scored_categories, default=(0, ""))
            # Uma palavra solta (por exemplo, "warning" na legenda de um desenho)
            # não é evidência suficiente para nomear uma seção. Um termo forte no
            # cabeçalho/início da página, por outro lado, é uma evidência válida.
            heading_text = text[:180]
            primary_terms = {
                "Segurança": ("safety", "segurança", "danger"),
                "Instalação e comissionamento": ("installation", "instala", "mounting", "wiring", "commission"),
                "Operação": ("operation", "operaç", "operating", "start", "controle"),
                "Dados técnicos": ("technical data", "dados técnicos", "specification", "rating", "tensão"),
                "Manutenção e diagnóstico": ("maintenance", "manuten", "troubleshoot", "fault", "diagnostic"),
            }
            has_primary_heading = any(
                term in heading_text for term in primary_terms.get(matched_title, ())
            )
            continues_confirmed_topic = (
                score > 0
                and matched_title == last_category
                and last_page_number is not None
                and page.number == last_page_number + 1
            )
            if score >= 2 or has_primary_heading or continues_confirmed_topic:
                buckets[matched_title].append(page.number)
                last_category = matched_title
            elif (
                len(text) >= 80
                and last_category is not None
                and last_page_number is not None
                and page.number == last_page_number + 1
            ):
                # Páginas consecutivas pouco textuais (diagramas, tabelas ou listas)
                # frequentemente continuam o assunto da página anterior.
                buckets[last_category].append(page.number)
            elif len(text) >= 80:
                remaining.append(page.number)
                last_category = None
            else:
                last_category = None
            last_page_number = page.number

        selected: list[int] = []
        sections: list[PdfStructureSection] = []
        for title, _terms in categories:
            page_numbers = [number for number in buckets[title] if number not in selected]
            if page_numbers:
                allowed = page_numbers[: max(0, selection_limit - len(selected))]
                if allowed:
                    selected.extend(allowed)
                    evidence = self._local_page_evidence(allowed, pages)
                    sections.append(
                        PdfStructureSection(
                            title=title,
                            page_numbers=allowed,
                            intro=self._local_source_intro(allowed, pages),
                            evidence=evidence,
                        )
                    )
        if len(selected) < selection_limit:
            allowed = [number for number in remaining if number not in selected][
                : selection_limit - len(selected)
            ]
            if allowed:
                selected.extend(allowed)
                sections.append(
                    PdfStructureSection(
                        title=self._local_section_title(allowed, pages),
                        page_numbers=allowed,
                        intro=self._local_source_intro(allowed, pages),
                        evidence=self._local_page_evidence(allowed, pages),
                    )
                )

        if not sections and pages:
            selected = [page.number for page in pages[:selection_limit] if page.analysis_text.strip()]
            if selected:
                sections.append(
                    PdfStructureSection(
                        title="Conteúdo técnico selecionado",
                        page_numbers=selected,
                        intro=self._local_source_intro(selected, pages),
                        evidence=self._local_page_evidence(selected, pages),
                    )
                )

        available = {page.number for page in pages}
        return PdfStructurePlan(
            document_title=manual_title.strip(),
            sections=sections,
            selected_page_numbers=sorted(selected),
            omitted_page_numbers=sorted(available - set(selected)),
        )

    @staticmethod
    def _local_section_title(page_numbers: list[int], pages: list[PdfPage]) -> str:
        """Use a visible heading as the local section title whenever possible."""
        selected = set(page_numbers)
        ignored = {
            "technical documentation", "technical manual", "manual", "contents",
            "table of contents", "page", "notes", "notes:",
        }
        for page in pages:
            if page.number not in selected:
                continue
            for raw_line in page.analysis_text.splitlines()[:18]:
                line = re.sub(r"\s+", " ", raw_line).strip(" -–—:|")
                letters = sum(character.isalpha() for character in line)
                if (
                    4 <= len(line) <= 90
                    and letters >= 4
                    and not re.fullmatch(r"[\d\W_]+", line)
                    and line.lower() not in ignored
                ):
                    return line[:90]
        return "Informações técnicas selecionadas"

    def _source_backed_intro(
        self,
        value: object,
        page_numbers: list[int],
        pages: list[PdfPage],
    ) -> str:
        """Reject boilerplate AI summaries in favour of actual selected-page content."""
        intro = self._compact_text(value, 500)
        generic_patterns = (
            "é fundamental",
            "e fundamental",
            "deve ser feita com cuidado",
            "importante para garantir",
            "funcionamento correto",
            "conteúdo técnico selecionado",
            "conteudo tecnico selecionado",
            "páginas técnicas selecionadas",
            "paginas tecnicas selecionadas",
            "conforme as instruções",
            "conforme instruções",
        )
        normalized = intro.lower()
        if not intro or any(pattern in normalized for pattern in generic_patterns):
            return self._local_source_intro(page_numbers, pages)
        return intro

    @staticmethod
    def _local_source_intro(page_numbers: list[int], pages: list[PdfPage]) -> str:
        """Reuse actual source sentences as a neutral, auditable fallback introduction.

        The introductory block is placed in the editable section before its pages. Returning
        real content is preferable to inventing a generic Portuguese sentence that suggests
        technical completeness without conveying the manufacturer instructions.
        """
        selected = set(page_numbers)
        snippets: list[str] = []
        total_length = 0
        for page in pages:
            if page.number not in selected:
                continue
            text = re.sub(r"\s+", " ", page.analysis_text).strip()
            if not text:
                continue
            for sentence in re.split(r"(?<=[.!?])\s+", text):
                sentence = sentence.strip()
                if len(sentence) < 35:
                    continue
                if total_length + len(sentence) > 460:
                    break
                snippets.append(sentence)
                total_length += len(sentence) + 1
                if len(snippets) >= 2:
                    break
            if len(snippets) >= 2 or total_length >= 460:
                break
        return " ".join(snippets) or ManualAIService._local_page_evidence(page_numbers, pages)

    @staticmethod
    def _local_page_evidence(page_numbers: list[int], pages: list[PdfPage]) -> str:
        """Produce a short literal excerpt so local selections remain auditable in the UI."""
        selected = {number for number in page_numbers}
        for page in pages:
            if page.number in selected:
                excerpt = ManualAIService._compact_text(page.analysis_text, 180)
                if excerpt:
                    return excerpt
        return ""

    def generate_section_text(self, section_title: str, context_topic: str) -> str:
        """Generate professional technical descriptive text for a manual section using AI."""
        if self._client is None:
            return f"Texto técnico descritivo gerado automaticamente para a seção '{section_title}'."

        prompt = (
            f"Escreva um texto técnico profissional em português para a seção '{section_title}' de um manual técnico sobre '{context_topic}'. "
            f"O texto deve ser claro, objetivo, orientativo para operadores e seguir o padrão de engenharia industrial. Retorne apenas o texto descritivo."
        )
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=400,
            )
            return response.choices[0].message.content.strip()
        except Exception as error:
            return f"Erro ao gerar texto técnico: {error}"
