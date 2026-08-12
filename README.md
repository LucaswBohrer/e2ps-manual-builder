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
* **💾 Projeto E2PS (`.e2ps`)**: Salve e reabra o trabalho em andamento com as páginas, recortes, capa, seções, subseções, ordem dos blocos de texto e modo de exportação de cada página.
* **🔐 Configuração de IA Persistente**: A API Key, a Base URL e o modelo selecionado podem ser salvos localmente no computador para reutilização ao reiniciar o aplicativo. A chave nunca é armazenada dentro do arquivo `.e2ps`.

---

# 🚀 Instalação e Execução

```bash
git clone https://github.com/LuquinhasBohrer/e2ps-manual-builder.git
cd e2ps-manual-builder
pip install -r requirements.txt
python main.py
```

---

# 💾 Salvar e Retomar um Manual

Após adicionar páginas, recortes e estruturar o manual, use **Save Project (.e2ps)** na barra superior. O arquivo `.e2ps` é portátil e contém todos os recursos necessários para continuar o trabalho em outro momento, inclusive os arquivos de página e a capa selecionada.

Para retomar, use **Open Project (.e2ps)** e selecione o arquivo salvo. O aplicativo reabrirá as páginas, os recortes, a estrutura do manual e os blocos de texto na mesma organização em que foram salvos.

> A credencial de IA não faz parte do arquivo `.e2ps`, evitando que ela seja compartilhada acidentalmente ao enviar o projeto. Use **Salvar Configs** no painel de IA para mantê-la apenas neste computador.

---

# 🏗️ Arquitetura dos Módulos

| Módulo               | Responsabilidade                      |
| -------------------- | ------------------------------------- |
| `main_window.py`     | Interface gráfica e painel de IA      |
| `ai_service.py`      | Sugestão de estrutura e geração de texto |
| `translation_service.py` | Tradução de textos e imagens via Manus AI |
| `project_service.py` | Geração de projetos R Markdown        |
| `project_file_service.py` | Leitura e gravação de projetos portáteis `.emb` |
| `export_worker.py`   | Exportação multilíngue em segundo plano |
| `models.py`          | Modelos de dados (Seções, Subseções, Páginas) |

---

# 📄 Licença
Desenvolvido para otimizar e padronizar a criação de manuais técnicos.
