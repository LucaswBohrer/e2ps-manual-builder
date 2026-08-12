# 📘 E2PS Manual Builder (AI Powered)

> Aplicação desktop desenvolvida para automatizar a criação da estrutura inicial de manuais técnicos da E2PS a partir de arquivos PDF, agora com **Inteligência Artificial (Manus AI)** integrada.

O **E2PS Manual Builder** agiliza a produção de manuais técnicos, eliminando tarefas repetitivas e adicionando recursos inteligentes como sugestão automática de estrutura, geração de textos técnicos por IA, edição de blocos de texto entre imagens, upload de capa personalizada e tradução multilíngue de páginas.

---

# ✨ Funcionalidades Principais

* **🤖 Assistente de Inteligência Artificial**: Analisa o PDF aberto e sugere automaticamente seções, subseções, distribuição de páginas e textos técnicos.
* **✍️ Geração e Edição de Texto de Seção**: Adicione textos descritivos personalizados entre as imagens de cada seção ou peça para a IA gerá-los automaticamente.
* **🖼️ Upload de Capa do Manual**: Selecione diretamente na interface a imagem da capa (`Capa.png`) para que o projeto seja exportado pronto.
* **🌐 Tradução Multilíngue Completa**: Exportação simultânea para múltiplos idiomas (**Português, Inglês e Espanhol**) com tradução integrada via Manus AI.
* **✂️ Recorte de Páginas (Crop)**: Ferramenta visual para recortar trechos de páginas do PDF, gerando variantes independentes.
* **🎨 Identidade Visual E2PS**: Inclusão automática de logotipos, fontes e layout oficial em R Markdown.

---

# 🚀 Instalação e Execução

```bash
git clone https://github.com/LuquinhasBohrer/e2ps-manual-builder.git
cd e2ps-manual-builder
pip install -r requirements.txt
python main.py
```

---

# 🏗️ Arquitetura dos Módulos

| Módulo               | Responsabilidade                      |
| -------------------- | ------------------------------------- |
| `main_window.py`     | Interface gráfica e painel de IA      |
| `ai_service.py`      | Sugestão de estrutura e geração de texto |
| `translation_service.py` | Tradução de textos e imagens via Manus AI |
| `project_service.py` | Geração de projetos R Markdown        |
| `export_worker.py`   | Exportação multilíngue em segundo plano |
| `models.py`          | Modelos de dados (Seções, Subseções, Páginas) |

---

# 📄 Licença
Desenvolvido para otimizar e padronizar a criação de manuais técnicos.
