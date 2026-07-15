# 📘 E2PS Manual Builder

> Aplicação desktop desenvolvida para automatizar a criação da estrutura inicial de manuais técnicos da E2PS a partir de arquivos PDF.

O **E2PS Manual Builder** foi criado para agilizar a produção de manuais técnicos, eliminando tarefas repetitivas como selecionar páginas, exportar imagens, organizar diretórios e criar a estrutura inicial em **R Markdown**.

Com poucos cliques, a aplicação gera um projeto completo, pronto para edição e posterior geração do manual em PDF.

---

# ✨ Funcionalidades

* 📄 Importação de arquivos PDF.
* 🖼️ Visualização de todas as páginas em miniaturas.
* 🔍 Pré-visualização ampliada da página selecionada.
* ✅ Seleção individual das páginas desejadas.
* ☑️ Seleção e desmarcação de todas as páginas.
* 📂 Organização das páginas em seções do manual.
* 📝 Geração automática da estrutura do manual em **R Markdown**.
* 🖼️ Exportação das páginas selecionadas em formato PNG.
* 📁 Criação automática da estrutura de pastas do projeto.
* 🎨 Inclusão automática da identidade visual da E2PS (logo, fontes e layout).
* ⚡ Processamento rápido utilizando **PyMuPDF**.
* 🌙 Interface moderna desenvolvida com **PySide6**.

---

# 🖥️ Visão Geral

O fluxo de utilização da aplicação é bastante simples:

```text
Abrir PDF
     │
     ▼
Selecionar as páginas
     │
     ▼
Organizar em seções
     │
     ▼
Informar os dados do manual
     │
     ▼
Exportar projeto
     │
     ▼
Editar o arquivo manual.rmd
     │
     ▼
Gerar o PDF final
```

---

# 📁 Estrutura do Projeto Gerado

Após a exportação, a aplicação cria automaticamente uma estrutura semelhante à seguinte:

```text
Projeto/

├── img/
│   ├── pagina001.png
│   ├── pagina002.png
│   └── ...
│
├── output/
│
├── manual.rmd
├── logo.png
└── Gotham Rounded/
```

Todo o projeto já fica organizado e preparado para edição.

---

# 🚀 Instalação

## Pré-requisitos

* Python 3.10 ou superior
* R *(opcional)*
* Pandoc *(opcional)*

> O R e o Pandoc são necessários apenas para gerar o PDF final a partir do arquivo `manual.rmd`.

---

## Clonando o repositório

```bash
git clone https://github.com/LuquinhasBohrer/e2ps-manual-builder.git

cd e2ps-manual-builder
```

---

## Criando um ambiente virtual

### Windows

```powershell
python -m venv .venv

.\.venv\Scripts\Activate.ps1
```

### Linux / macOS

```bash
python3 -m venv .venv

source .venv/bin/activate
```

---

## Instalando as dependências

```bash
pip install -r requirements.txt
```

---

## Executando a aplicação

```bash
python main.py
```

---

# 📖 Como utilizar

1. Abra um arquivo PDF.
2. Selecione apenas as páginas que farão parte do manual.
3. Organize as páginas em seções conforme necessário.
4. Informe os dados do manual (título, código, ano e semestre).
5. Clique em **Exportar Projeto**.
6. Edite o arquivo `manual.rmd` conforme necessário.
7. Gere o PDF final utilizando R Markdown.

---

# 🏗️ Estrutura do Projeto

```text
E2PS-Manual-Builder/

├── main.py
├── requirements.txt
│
└── manual_builder/
    ├── main_window.py
    ├── models.py
    ├── pdf_service.py
    ├── project_service.py
    ├── styles.py
    └── workers.py
```

---

# 🧩 Arquitetura

O projeto foi desenvolvido seguindo uma arquitetura modular, facilitando manutenção e futuras evoluções.

| Módulo               | Responsabilidade                      |
| -------------------- | ------------------------------------- |
| `main_window.py`     | Interface gráfica                     |
| `pdf_service.py`     | Processamento e renderização dos PDFs |
| `project_service.py` | Geração do projeto R Markdown         |
| `workers.py`         | Processamento em segundo plano        |
| `models.py`          | Modelos de dados                      |
| `styles.py`          | Tema e estilos da aplicação           |

---

# 🛣️ Evoluções Futuras

Algumas funcionalidades planejadas para versões futuras incluem:

* 🤖 Organização automática das páginas utilizando Inteligência Artificial.
* 📝 Sugestão automática de capítulos.
* 🔍 OCR para extração de texto.
* 📄 Comparação entre versões de PDFs.
* ⚙️ Personalização de templates.
* 📊 Melhorias na exportação dos projetos.

---

# 🔒 Privacidade

Todo o processamento dos documentos é realizado **localmente**.

Nenhum arquivo PDF é enviado para servidores externos, garantindo maior segurança e confidencialidade das informações.

---

# 🛠️ Tecnologias Utilizadas

* Python
* PySide6
* PyMuPDF
* R Markdown
* Pandoc
* Qt

---

# 📄 Licença

Este projeto foi desenvolvido para uso interno da **E2PS**, com o objetivo de otimizar e padronizar a criação de manuais técnicos.
