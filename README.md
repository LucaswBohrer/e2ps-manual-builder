<div align="center">

# 🧰 E2PS Manual Builder

### Monte, organize, traduza e exporte manuais técnicos com uma interface visual e assistência de IA.

[![Status](https://img.shields.io/badge/status-em%20desenvolvimento-F58220?style=for-the-badge&labelColor=1F2937)](https://github.com/LuquinhasBohrer/e2ps-manual-builder)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Desktop](https://img.shields.io/badge/Interface-PySide6-41CD52?style=for-the-badge&logo=qt&logoColor=white)](https://doc.qt.io/qtforpython-6/)
[![Projeto](https://img.shields.io/badge/Projeto-.e2ps-6B46C1?style=for-the-badge&labelColor=1F2937)](#-projetos-e2ps-continuidade-do-trabalho)
[![Exportação](https://img.shields.io/badge/Exportação-R%20Markdown-276DC3?style=for-the-badge&labelColor=1F2937)](#-exportação-em-r-markdown-e-pdf)

[Começar agora](#-instalação-rápida) · [Fluxo de trabalho](#-fluxo-de-trabalho) · [IA e tradução](#-ia-e-tradução) · [Salvar projeto](#-projetos-e2ps-continuidade-do-trabalho) · [Ajuda](#-solução-de-problemas)

</div>

---

## ✨ O que é o E2PS Manual Builder?

O **E2PS Manual Builder** é uma aplicação desktop criada para acelerar a preparação de manuais técnicos a partir de PDFs ou imagens. Ele transforma um conjunto de páginas soltas em um projeto editorial organizado: você seleciona o conteúdo relevante, cria recortes, define seções, escreve explicações e exporta a estrutura para **R Markdown**, pronta para revisão e geração de PDF.

> **Pensado para manuais extensos:** salve o progresso em um arquivo portátil `.e2ps`, feche o aplicativo sem medo e retome o trabalho exatamente do ponto em que parou.

---

## 🚀 Principais recursos

| Recurso | O que você pode fazer |
|:--|:--|
| 📄 **PDFs e imagens** | Abrir um PDF completo ou importar várias imagens diretamente para a montagem do manual. |
| ✂️ **Recortes ilimitados** | Criar mais de um recorte da mesma página e utilizar cada variante como um item independente. |
| 🧱 **Seções flexíveis** | Criar, renomear e editar seções e subseções depois de iniciadas. |
| ✍️ **Texto entre imagens** | Inserir explicações antes, entre ou após qualquer imagem de uma seção. |
| 🖼️ **Capa personalizada** | Selecionar uma imagem de capa diretamente pela interface. |
| 🤖 **Assistente de IA** | Pedir sugestões de estrutura, gerar textos de apoio e conversar sobre o manual carregado. |
| 🌍 **Tradução técnica** | Exportar em português, inglês e espanhol, escolhendo página a página entre imagem original ou texto/tabela editável. |
| 💾 **Projetos `.e2ps`** | Salvar e reabrir todo o trabalho, incluindo páginas, recortes, capa, estrutura e textos. |
| 📦 **R Markdown** | Gerar uma estrutura organizada para compilar o manual em PDF. |

---

## 🧭 Fluxo de trabalho

```mermaid
flowchart LR
    A[📄 PDF ou imagens] --> B[✂️ Selecionar páginas e criar recortes]
    B --> C[🧱 Montar seções e subseções]
    C --> D[✍️ Inserir textos e definir modos de tradução]
    D --> E[💾 Salvar projeto .e2ps]
    E --> F[📦 Exportar R Markdown]
    F --> G[📘 Revisar e compilar PDF]

    classDef input fill:#E8F1FF,stroke:#3776AB,color:#172554;
    classDef edit fill:#FFF4E6,stroke:#F58220,color:#7C2D12;
    classDef save fill:#F3E8FF,stroke:#6B46C1,color:#3B0764;
    classDef output fill:#EAF8EE,stroke:#1E8E3E,color:#14532D;

    class A input;
    class B,C,D edit;
    class E save;
    class F,G output;
```

O aplicativo foi concebido para trabalhar de forma incremental. Você pode começar pela seleção de imagens, organizar apenas uma parte do manual, salvar o projeto e continuar depois — sem precisar repetir a estrutura já construída.

---

## ⚡ Instalação rápida

### 1. Pré-requisito

Tenha o **Python 3.10 ou superior** instalado. A interface é baseada em PySide6 e as dependências do aplicativo estão declaradas em `requirements.txt`.

### 2. Clone e instale

```bash
git clone https://github.com/LuquinhasBohrer/e2ps-manual-builder.git
cd e2ps-manual-builder
python -m pip install -r requirements.txt
```

### 3. Inicie o aplicativo

```bash
python main.py
```

No Windows, caso `python` não seja reconhecido, substitua o comando por `py`:

```powershell
py -m pip install -r requirements.txt
py main.py
```

| Dependência | Finalidade |
|:--|:--|
| `PySide6` | Interface gráfica desktop. |
| `PyMuPDF` | Leitura de PDFs, renderização de páginas e extração de texto. |
| `Pillow` | Importação, conversão e geração de miniaturas de imagens. |
| `openai` | Comunicação com provedores compatíveis com a API OpenAI. |

---

## 🛠️ Fluxo de trabalho

### 📥 1. Carregue o material

Use **Open PDF** para abrir documentos PDF ou **Open Images** para importar imagens prontas. As páginas são exibidas em miniaturas e na área central de pré-visualização.

### ✂️ 2. Crie recortes quando necessário

Selecione uma página e use a ferramenta de recorte. Você pode criar várias variantes da mesma página, por exemplo, uma tabela, um esquema elétrico e uma observação localizada. Cada recorte pode ser enviado a uma seção diferente.

### 🧩 3. Estruture o manual

Crie seções e subseções na árvore de conteúdo. Elas continuam editáveis após a criação: renomeie títulos, reorganize o conteúdo e ajuste o manual conforme a necessidade técnica.

### 📝 4. Combine imagens e explicações

Cada seção suporta uma sequência mista de blocos. Isso permite colocar uma imagem, inserir um texto explicativo, acrescentar outra imagem e concluir com uma observação ou tabela.

> Organize a sequência dentro da seção **antes de exportar**, pois ela define a ordem do conteúdo no R Markdown e no PDF final.

### 🎨 5. Defina a capa

Use a opção de capa para selecionar uma imagem que será copiada automaticamente para o projeto exportado.

### 💾 6. Salve o andamento

Antes de fechar o aplicativo — e ao concluir cada etapa importante — use **Save Project (.e2ps)**. Consulte a seção de continuidade do trabalho para entender o que é salvo.

---

## 🤖 IA e tradução

### 💬 Assistente de IA

O painel de IA permite fazer perguntas sobre o manual, solicitar textos técnicos de apoio e obter sugestões de como distribuir as páginas entre seções e subseções. A sugestão serve como orientação; ela **não altera automaticamente** a estrutura do manual, deixando a decisão final com você.

### ☁️ Configuração com GroqCloud

O aplicativo aceita serviços compatíveis com a API OpenAI. Para usar GroqCloud, informe sua chave, a URL-base e um modelo disponível na sua conta. Uma URL-base comum é:

```text
https://api.groq.com/openai/v1
```

Depois de configurar, utilize **Salvar Configs**. A API Key, a URL-base e o modelo ficam disponíveis nas próximas aberturas do aplicativo no mesmo computador e perfil de usuário.

> 🔐 **Importante:** a sua chave de IA nunca é gravada no arquivo `.e2ps`. Ela permanece apenas nas preferências locais do computador.

### 🌐 Modos de exportação por página

| Modo | Indicado para | Resultado |
|:--|:--|:--|
| 🖼️ **Imagem** | Diagramas, símbolos, certificados, desenhos ou páginas cuja aparência precisa ser preservada. | Copia a imagem original para o projeto sem inserir texto bruto da IA sobre a figura. |
| 📊 **Texto/Tabela (OCR)** | Especificações, tabelas técnicas, listas de parâmetros, avisos e páginas com muito texto. | Solicita extração estruturada e tradução para gerar texto e tabelas editáveis no R Markdown. |

Para tabelas técnicas que precisam sair em português de forma legível, priorize **Texto/Tabela (OCR)**. Revise sempre números, unidades, referências normativas, símbolos e valores críticos antes de publicar um manual oficial.

Se a IA não conseguir extrair uma página, o aplicativo preserva a imagem original. Ele não deve inserir mensagens de erro no arquivo `.Rmd` nem no PDF final.

---

## 💾 Projetos `.e2ps`: continuidade do trabalho

O formato **`.e2ps`** é o arquivo de projeto oficial do E2PS Manual Builder. Ele é portátil e foi criado para que manuais grandes possam ser interrompidos e retomados com segurança.

| Elemento salvo no projeto | Incluído? |
|:--|:--:|
| Páginas de PDF e imagens importadas | ✅ |
| Recortes e miniaturas | ✅ |
| Imagem de capa | ✅ |
| Seções e subseções | ✅ |
| Textos inseridos e ordem dos blocos | ✅ |
| Idiomas e modo de exportação de cada página | ✅ |
| API Key do provedor de IA | ❌ |

### Salvar e abrir

| Ação | Como usar |
|:--|:--|
| 💾 **Salvar projeto** | Clique em **Save Project (.e2ps)**, escolha a pasta e informe o nome. A extensão `.e2ps` é adicionada automaticamente. |
| 📂 **Abrir projeto** | Clique em **Open Project (.e2ps)** e selecione o arquivo salvo. O conteúdo editável será restaurado na interface. |
| 🔁 **Migrar projeto antigo** | Arquivos legados `.emb` ainda podem ser abertos. Ao salvar novamente, passam a usar `.e2ps`. |

> Faça cópias de segurança periódicas dos projetos `.e2ps`, principalmente antes de grandes reorganizações. Mantenha também os PDFs e imagens de origem em uma pasta organizada.

---

## 📦 Exportação em R Markdown e PDF

A exportação gera uma pasta organizada por idioma com o arquivo `.Rmd`, imagens e outros ativos necessários para a compilação do manual. A interface permite selecionar **Português**, **Inglês** e **Espanhol** conforme a necessidade do projeto.

Para renderizar o PDF, abra o arquivo `.Rmd` em um ambiente com R Markdown configurado, como o RStudio, e execute:

```r
rmarkdown::render("manual.Rmd")
```

> A compilação em PDF depende de R, Pandoc, pacotes R e uma distribuição LaTeX. Esses componentes pertencem ao ambiente de R Markdown e não são instalados pelo aplicativo Python.

---

## 🩺 Solução de problemas

| Sintoma | Possível causa | O que fazer |
|:--|:--|:--|
| 💥 O terminal abre e fecha ao iniciar. | Dependência ausente ou erro de inicialização. | Abra um terminal na pasta do projeto, execute `python main.py` e instale as dependências com `python -m pip install -r requirements.txt`. |
| 🖼️ **Open Images** não funciona. | Pillow ausente no ambiente Python utilizado. | Execute `python -m pip install Pillow`. |
| 🔑 Erro 401 da IA. | Chave inválida ou pertencente a outro provedor. | Confirme a chave e a URL-base configurada. |
| 🤖 Erro 404 de modelo. | O modelo informado não existe no provedor escolhido. | Use um modelo disponível na sua conta; no Groq, modelos `gpt-*` não pertencem automaticamente ao catálogo. |
| 📏 Erro 413 / requisição grande. | Texto ou imagem excedeu o limite do provedor. | Divida o conteúdo em etapas ou reduza a quantidade de páginas analisadas de uma vez. |
| ⏳ Exportação lenta. | Páginas em Texto/Tabela são analisadas individualmente. | Acompanhe o percentual, exporte em etapas ou use o modo Imagem para diagramas e figuras. |
| 📁 A pasta de exportação apareceu sem imagens. | A exportação ainda está processando ou uma análise visual demorou. | Aguarde a conclusão; as versões atuais copiam imagens antes da chamada à IA. |
| 🌍 Conteúdo permanece no idioma original. | A página foi exportada como Imagem ou a extração precisa de revisão. | Use Texto/Tabela para conteúdo textual e revise o `.Rmd` antes de gerar o PDF. |
| 🧩 O projeto não abre. | Arquivo corrompido ou inválido. | Tente uma cópia de segurança `.e2ps` e mantenha os arquivos em local confiável. |

---

## 🧱 Arquitetura do projeto

| Módulo | Responsabilidade |
|:--|:--|
| `main.py` | Ponto de entrada da aplicação. |
| `manual_builder/main_window.py` | Janela principal, páginas, seções, configurações de IA e ações de projeto. |
| `manual_builder/models.py` | Modelos de páginas, seções e subseções. |
| `manual_builder/pdf_service.py` | Leitura de PDFs, renderização de páginas e texto. |
| `manual_builder/crop_dialog.py` | Interface de criação de recortes. |
| `manual_builder/ai_service.py` | Chat, sugestões de estrutura e geração de textos. |
| `manual_builder/translation_service.py` | Tradução, análise visual e extração estruturada. |
| `manual_builder/project_service.py` | Geração de R Markdown e organização de ativos. |
| `manual_builder/export_worker.py` | Exportação em segundo plano e progresso. |
| `manual_builder/project_file_service.py` | Leitura e gravação de projetos `.e2ps`. |
| `manual_builder/workers.py` | Tarefas em segundo plano de carregamento. |
| `manual_builder/styles.py` | Estilos da interface Qt. |

---

## 🧪 Teste de persistência

O repositório inclui um teste local que verifica a criação e a reabertura de projetos `.e2ps`, incluindo páginas, recortes, capa, blocos de texto e preferências de IA.

```bash
python test_project_persistence.py
```

---

<div align="center">

### 🛡️ Segurança e boas práticas

Mantenha a API Key em sigilo, não a envie junto com o projeto e revise qualquer tradução gerada por IA antes de publicar um documento técnico.

**E2PS Manual Builder** · Estruture primeiro. Revise sempre. Exporte com confiança.

</div>
