"""AI assistant service for automated manual structuring and technical text generation."""

from __future__ import annotations

import json
import os
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from manual_builder.models import PdfPage, ManualSection, ManualSubsection


class ManualAIService:
    """Service utilizing Manus AI to suggest manual structures and generate technical content."""

    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY", "sandbox-key")
        base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        if OpenAI is not None:
            self._client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            self._client = None

    def suggest_structure(self, pages: list[PdfPage], manual_title: str) -> list[ManualSection]:
        """Ask AI to analyze available pages and suggest a professional technical manual structure."""
        if self._client is None or not pages:
            # Fallback default structure if AI is unavailable
            return [
                ManualSection(
                    title="Introduction and Overview",
                    pages=pages[:min(2, len(pages))],
                    text_content="General overview and technical specifications of the equipment.",
                ),
                ManualSection(
                    title="Operation and Technical Information",
                    pages=pages[min(2, len(pages)):],
                    text_content="Step-by-step operating instructions and safety guidelines.",
                ),
            ]

        page_summary = ", ".join(f"Page {p.number}" for p in pages)
        prompt = (
            f"You are a technical documentation expert. We have a technical manual titled '{manual_title}' with {len(pages)} pages: [{page_summary}].\n"
            f"Suggest a professional logical structure for this manual in JSON format. "
            f"Return a JSON array of sections. Each section must have 'title' (string), 'text_content' (technical description in Portuguese), 'page_numbers' (list of integers), "
            f"and optional 'subsections' (list of objects with 'title', 'text_content', and 'page_numbers').\n"
            f"Return ONLY valid JSON with no markdown wrapping or extra text."
        )

        try:
            response = self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            raw_content = response.choices[0].message.content.strip()
            if raw_content.startswith("```json"):
                raw_content = raw_content[7:]
            if raw_content.endswith("```"):
                raw_content = raw_content[:-3]
            data = json.loads(raw_content.strip())

            page_map = {p.number: p for p in pages}
            sections: list[ManualSection] = []

            for item in data:
                sec_title = item.get("title", "Section")
                sec_text = item.get("text_content", "")
                sec_page_nums = item.get("page_numbers", [])
                sec_pages = [page_map[num] for num in sec_page_nums if num in page_map]

                subsections: list[ManualSubsection] = []
                for sub in item.get("subsections", []):
                    sub_title = sub.get("title", "Subsection")
                    sub_text = sub.get("text_content", "")
                    sub_page_nums = sub.get("page_numbers", [])
                    sub_pages = [page_map[num] for num in sub_page_nums if num in page_map]
                    subsections.append(ManualSubsection(title=sub_title, pages=sub_pages, text_content=sub_text))

                sections.append(ManualSection(title=sec_title, pages=sec_pages, subsections=subsections, text_content=sec_text))

            return sections if sections else self._fallback_structure(pages)
        except Exception:
            return self._fallback_structure(pages)

    def generate_section_text(self, section_title: str, context_topic: str) -> str:
        """Generate professional technical descriptive text for a manual section using AI."""
        if self._client is None:
            return f"Instruções técnicas detalhadas referentes à seção {section_title}."

        prompt = (
            f"Escreva um texto técnico profissional em português para a seção '{section_title}' de um manual técnico sobre '{context_topic}'. "
            f"O texto deve ser claro, objetivo, orientativo para operadores e seguir o padrão de engenharia industrial. Retorne apenas o texto descritivo."
        )
        try:
            response = self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return f"Descrição técnica oficial para {section_title}."

    def _fallback_structure(self, pages: list[PdfPage]) -> list[ManualSection]:
        """Fallback structure if JSON parsing fails."""
        return [
            ManualSection(
                title="Visão Geral e Especificações",
                pages=pages[:max(1, len(pages) // 2)],
                text_content="Especificações técnicas gerais e introdução ao equipamento.",
            ),
            ManualSection(
                title="Operação e Procedimentos",
                pages=pages[max(1, len(pages) // 2):],
                text_content="Instruções operacionais e diretrizes de segurança.",
            ),
        ]
