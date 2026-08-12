"""AI assistant service for automated manual structuring and technical text generation."""

from __future__ import annotations

import os
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from manual_builder.models import PdfPage


class ManualAIService:
    """Service utilizing Manus AI to chat, suggest manual structures, and generate technical content."""

    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY", "sandbox-key")
        base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        if OpenAI is not None:
            self._client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            self._client = None
        self._chat_history = [
            {"role": "system", "content": "You are a professional technical documentation assistant for E2PS manuals. Help the user structure manuals, choose which pages go into which sections, and write professional technical descriptions in Portuguese."}
        ]

    def ask_ai(self, user_message: str, pages_summary: str = "") -> str:
        """Chat with the AI assistant, asking for suggestions, page distribution, or writing help."""
        if self._client is None:
            return "Serviço de IA indisponível (OpenAI client não carregado)."

        context_msg = f"Available pages in PDF: [{pages_summary}].\nUser query: {user_message}"
        self._chat_history.append({"role": "user", "content": context_msg})

        try:
            response = self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=self._chat_history,
                temperature=0.4,
            )
            reply = response.choices[0].message.content.strip()
            self._chat_history.append({"role": "assistant", "content": reply})
            return reply
        except Exception as error:
            return f"Erro ao comunicar com a IA: {error}"

    def suggest_structure_text(self, pages: list[PdfPage], manual_title: str) -> str:
        """Ask AI to analyze pages and give text suggestions on how to structure the manual."""
        page_summary = ", ".join(f"Página {p.number}" for p in pages)
        prompt = (
            f"Analise as {len(pages)} páginas deste PDF ({page_summary}) para o manual '{manual_title}'. "
            f"Sugira em português quais páginas devem pertencer a cada seção principal e subseção, "
            f"explicando o raciocínio para que o usuário possa fazer os recortes necessários e organizar manualmente."
        )
        return self.ask_ai(prompt, page_summary)

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
