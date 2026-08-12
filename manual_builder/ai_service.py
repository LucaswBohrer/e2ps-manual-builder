"""AI assistant service for automated manual structuring and technical text generation with real PDF text context."""

from __future__ import annotations

import os
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from manual_builder.models import PdfPage


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
        """Ask AI to analyze concise page contents and suggest manual structure without hitting token limits."""
        if self._client is None:
            return "[Modo Auxiliar] Configure sua API Key para obter sugestões baseadas no conteúdo real do PDF."

        content_snippets = []
        # Take at most 30 pages or sample them, and truncate snippet to 120 chars to stay well under TPM limits
        sampled_pages = pages[:30]
        for p in sampled_pages:
            snippet = p.extracted_text[:120].replace("\n", " ").strip()
            if snippet:
                content_snippets.append(f"P.{p.number}: {snippet}")
        
        full_context = " | ".join(content_snippets)
        prompt = (
            f"Analise estas {len(sampled_pages)} páginas do PDF '{manual_title}':\n{full_context}\n\n"
            f"Sugira em português uma estrutura lógica de seções (ex: Introdução, Instalação, Operação, Manutenção) "
            f"indicando quais páginas devem pertencer a cada parte, de forma concisa e direta."
        )

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": "You are a concise technical documentation assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=600,
            )
            return response.choices[0].message.content.strip()
        except Exception as error:
            return f"Erro ao gerar sugestão de estrutura ({self._model}): {error}"

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
