<div align="center">

# E2PS Manual Builder

### Estruture, traduza e exporte manuais técnicos com uma interface visual.

[![Windows](https://img.shields.io/badge/Windows-10%20%2F%2011-0078D4?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/LuquinhasBohrer/e2ps-manual-builder/releases/latest)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Interface](https://img.shields.io/badge/Interface-PySide6-41CD52?style=for-the-badge&logo=qt&logoColor=white)](https://doc.qt.io/qtforpython-6/)
[![Projetos](https://img.shields.io/badge/Projetos-.e2ps-6B46C1?style=for-the-badge&labelColor=1F2937)](#projetos-e2ps)
[![Exportação](https://img.shields.io/badge/Exportação-R%20Markdown-276DC3?style=for-the-badge&labelColor=1F2937)](#exportação-r-markdown-e-pdf)

**[Baixar para Windows](https://github.com/LuquinhasBohrer/e2ps-manual-builder/releases/latest)** · **[Como usar](#fluxo-de-trabalho)** · **[IA e tradução](#ia-e-tradução)** · **[Solução de problemas](#solução-de-problemas)**

</div>

---

## Visão geral

O **E2PS Manual Builder** é uma aplicação desktop para transformar PDFs, imagens e arquivos HTML/HTM em projetos de manuais técnicos organizados. O usuário seleciona o conteúdo relevante, cria recortes, organiza seções e subseções, adiciona explicações e exporta o resultado em **R Markdown**, pronto para revisão e geração de PDF.

> **O programa foi pensado para manuais extensos.** Salve o trabalho em um arquivo `.e2ps`, feche o aplicativo e retome depois com páginas, recortes, estrutura e textos preservados.

| Entrada | Tratamento no E2PS | Saída |
|:--|:--|:--|
| PDF técnico | Pré-visualização, texto selecionável, recortes e proposta de estrutura | Texto Markdown ou ilustração, conforme o tipo de página |
| Imagens | Importação em lote, organização e recortes | Figuras posicionadas no manual |
| HTML/HTM | Leitura de cabeçalhos, texto-fonte e indicação de imagens pendentes | Seções editáveis e conteúdo estruturado |

---

## Baixar e instalar no Windows

A forma recomendada de usar o E2PS Manual Builder é pelo instalador. Ele já inclui o programa e suas dependências; portanto, **não é necessário instalar Python nem abrir terminal**.

### Instalação em três passos

1. Abra a página de [**Releases do projeto**](https://github.com/LuquinhasBohrer/e2ps-manual-builder/releases/latest).
2. Baixe o arquivo **`E2PS-Manual-Builder-V2-Setup-2.0.0.exe`** na seção **Assets**.
3. Execute o instalador e abra **E2PS Manual Builder V2** pelo Menu Iniciar ou pelo atalho da Área de Trabalho.

> A versão V2 instala em uma pasta separada e pode coexistir com instalações V1. Não é necessário desinstalar a versão anterior.

| Distribuição | Quando usar | Conteúdo |
|:--|:--|:--|
| **Instalador `.exe`** | Recomendado para uso normal | Atalhos, associação de arquivos `.e2ps` e desinstalador do Windows |
| **Versão portátil `.zip`** | Uso temporário ou sem permissão para instalar | Pasta completa; extraia-a e execute `E2PSManualBuilder.exe` |

> O instalador não possui assinatura comercial. Caso o Windows mostre uma confirmação adicional na primeira abertura, verifique se o arquivo foi baixado da Release oficial deste repositório antes de continuar.

---

## Recursos principais

| Recurso | Descrição |
|:--|:--|
| **Importação de PDF, imagens e HTML** | Carrega manuais em vários formatos em uma única interface visual. |
| **Estrutura automática editável** | Sugere seções e subseções com base no documento, mantendo a edição final sob controle do usuário. |
| **Recortes ilimitados** | Crie vários recortes da mesma página para separar tabelas, diagramas e observações, agora com zoom e navegação para selecionar detalhes com precisão. |
| **Editor de seções** | Renomeie, crie, exclua e reordene seções e subseções a qualquer momento. |
| **Texto entre figuras** | Insira avisos, instruções, listas e explicações antes, entre ou depois das imagens. |
| **Capa personalizada** | Selecione qualquer arquivo de imagem, independentemente da extensão; o aplicativo valida o conteúdo e converte automaticamente para `Capa.png`. |
| **Tema claro ou escuro** | Alterne a aparência da interface a qualquer momento; a escolha é aplicada imediatamente e fica salva neste computador. |
| **Assistente de IA** | Faça perguntas sobre o manual, obtenha sugestões de estrutura e gere textos de apoio. |
| **Tradução técnica** | Exporte em português, inglês ou espanhol, escolhendo texto/tabela ou imagem para cada conteúdo. |
| **Projetos `.e2ps`** | Salve e reabra o trabalho completo sem perder a montagem já realizada. |
| **R Markdown** | Gere um projeto organizado para revisão e compilação posterior em PDF. |

---

## Fluxo de trabalho

```mermaid
flowchart LR
    A[PDF, imagens ou HTML] --> B[Selecionar páginas e criar recortes]
    B --> C[Organizar seções e subseções]
    C --> D[Adicionar texto e definir exportação]
    D --> E[Salvar projeto .e2ps]
    E --> F[Exportar R Markdown]
    F --> G[Revisar e gerar PDF]

    classDef source fill:#E8F1FF,stroke:#3776AB,color:#172554;
    classDef editing fill:#FFF4E6,stroke:#F58220,color:#7C2D12;
    classDef save fill:#F3E8FF,stroke:#6B46C1,color:#3B0764;
    classDef output fill:#EAF8EE,stroke:#1E8E3E,color:#14532D;

    class A source;
    class B,C,D editing;
    class E save;
    class F,G output;
```

### 1. Carregue o material

Use **Open PDF**, **Open Images** ou **Open HTML**. A origem é convertida em páginas com miniaturas e pré-visualização. Em PDFs, o aplicativo aproveita o texto selecionável; em HTML, aproveita a hierarquia de cabeçalhos e identifica as imagens que precisam ser revisadas ou recortadas.

Na área **Imagem da capa**, selecione o arquivo sem depender da extensão. O E2PS tenta reconhecer o conteúdo real, incluindo PNG, JPEG, WebP, AVIF, SVG e outros formatos disponíveis no ambiente. A imagem escolhida é normalizada para PNG antes de ser salva no projeto e exportada como `Capa.png`. Se o arquivo não for uma imagem válida, o aplicativo informa o erro sem alterar a capa anterior.

> Para carregar um HTML com fidelidade, mantenha o arquivo `.html` junto de suas imagens, folhas de estilo e outros recursos locais.

### 2. Crie recortes e selecione conteúdo

Use a ferramenta de recorte para separar uma tabela, um diagrama elétrico ou uma observação dentro da mesma página. Cada recorte pode ser inserido em uma parte diferente do manual. Na tela de recorte, use **+**, **−**, o controle deslizante ou **Ctrl + roda do mouse** para ampliar e reduzir. Quando a página estiver ampliada, arraste com o **botão do meio do mouse** ou use as barras de rolagem para navegar até a área específica; o retângulo selecionado continua sendo convertido para os pixels originais da imagem.

### 3. Organize o manual

Crie ou edite seções e subseções na árvore de conteúdo. Clique com o botão direito em uma seção para renomear, editar o conteúdo, excluir ou mover sua posição. Em **Editar conteúdo**, você pode incluir páginas, recortes e textos em qualquer ordem.

A análise automática de PDFs cria uma proposta inicial baseada em evidências textuais do próprio documento. Ela não substitui a revisão editorial: todas as páginas e seções propostas continuam editáveis antes da exportação.

### 4. Escolha o modo adequado para cada página

| Modo de exportação | Indicado para | Resultado |
|:--|:--|:--|
| **Imagem** | Diagramas, certificados, desenhos, esquemas e símbolos | Preserva a imagem original como ilustração. |
| **Texto/Tabela** | Procedimentos, avisos, especificações, listas e tabelas | Usa o texto-fonte selecionável para produzir Markdown editável e traduzível. |

Para conteúdo técnico predominantemente textual, prefira **Texto/Tabela**. Diagramas e desenhos dimensionais devem permanecer como imagem para preservar medidas, símbolos e geometria.

### 5. Salve antes de parar

Use **Save Project (.e2ps)** em pontos importantes do trabalho. O arquivo guarda o estado do projeto para que o manual possa ser retomado posteriormente.

---

## IA e tradução

O painel de IA permite pedir sugestões de estrutura, gerar textos de apoio e fazer perguntas sobre o manual carregado. A análise de PDF usa o conteúdo da fonte como evidência e mantém a proposta editável.

### Configuração com GroqCloud

O aplicativo aceita provedores compatíveis com a API OpenAI. Para GroqCloud, informe a chave de acesso, a URL-base e um modelo disponível em sua conta.

```text
https://api.groq.com/openai/v1
```

Salve a configuração pelo botão **Salvar Configs**. As preferências ficam armazenadas no computador atual, mas a chave de API **não** é gravada no arquivo `.e2ps`.

> **Política de exportação:** o texto selecionável do PDF é a fonte prioritária. A leitura visual é usada somente para páginas realmente sem texto, reduzindo custos, tempo de processamento e o risco de inserir páginas em idioma original como imagem.

---

## Projetos `.e2ps`

O `.e2ps` é o formato oficial de projeto do E2PS Manual Builder. No Windows instalado, basta dar duplo clique em um arquivo `.e2ps` para abrir o projeto diretamente no aplicativo.

| Elemento preservado | Incluído no `.e2ps` |
|:--|:--:|
| Páginas importadas, miniaturas e recortes | Sim |
| Imagem de capa | Sim |
| Seções, subseções e ordem dos blocos | Sim |
| Textos inseridos e modos de exportação | Sim |
| Chave de API da IA | **Não** |
| Preferência de tema claro/escuro | **Não** — fica salva localmente no computador |

| Ação | Como usar |
|:--|:--|
| **Salvar projeto** | Use **Save Project (.e2ps)**, escolha a pasta e informe o nome. |
| **Abrir projeto** | Use **Open Project (.e2ps)** ou dê duplo clique no arquivo após instalar o aplicativo. |
| **Migrar arquivo antigo** | Arquivos `.emb` legados ainda podem ser abertos; ao salvar, passam a usar `.e2ps`. |

Faça cópias de segurança periódicas, principalmente antes de reestruturar grandes partes do manual.

### Preferência visual local

No painel **Appearance**, use o campo **Application theme** para escolher **Light** ou **Dark**. A mudança é aplicada imediatamente em toda a interface, incluindo a barra de ferramentas, painéis, listas, pré-visualização, menus e cabeçalho E2PS. A preferência é salva em `QSettings` no computador atual e é restaurada na próxima abertura; ela não altera nem é incorporada ao arquivo `.e2ps`.

---

## Exportação R Markdown e PDF

A exportação cria uma pasta por idioma contendo o `.Rmd` e os ativos necessários. Para compilar o PDF, abra o arquivo no RStudio ou em outro ambiente com R Markdown configurado e execute:

```r
rmarkdown::render("manual.Rmd")
```

A compilação requer R, Pandoc, os pacotes R necessários e uma distribuição LaTeX. Esses componentes pertencem ao ambiente de R Markdown e não são instalados pelo E2PS Manual Builder.

---

## Solução de problemas

| Situação | Ação recomendada |
|:--|:--|
| O instalador não abre | Baixe novamente pela Release oficial e confirme se o download foi concluído. Se o Windows exibir proteção adicional, use somente o arquivo vindo do repositório oficial. |
| `DeleteFile falhou, código 5` ou `Acesso negado` ao atualizar | Feche o E2PS Manual Builder e tente novamente. As versões novas do instalador já solicitam o fechamento automático do programa; se o erro persistir, abra o Gerenciador de Tarefas, finalize `E2PSManualBuilder.exe` e execute o instalador novamente. Não escolha **Ignorar este arquivo**, pois isso mantém o executável antigo e as funções novas — como capas em qualquer extensão — não serão instaladas. |
| Erro 401 na IA | Revise a chave e a URL-base do provedor. |
| Erro 404 de modelo | Informe um modelo que exista na conta e no provedor configurados. |
| Erro 413 ou limite de requisição | Reduza a quantidade de páginas analisadas de uma vez; para PDFs grandes, trabalhe por seção. |
| Conteúdo saiu no idioma original | Altere páginas predominantemente textuais para **Texto/Tabela** e revise a configuração de tradução. |
| HTML ficou incompleto | Mantenha os recursos locais junto do HTML; para conteúdo dependente de login ou scripts, salve a página como PDF pelo navegador. |
| Projeto não abre | Tente uma cópia anterior do `.e2ps` e mantenha os arquivos de trabalho em uma pasta confiável. |
| O PDF não gera no RStudio | Verifique se R, Pandoc e LaTeX estão configurados corretamente no ambiente de R Markdown. |

---

## Desenvolvimento local

Para desenvolver ou alterar o programa diretamente pelo código-fonte, instale Python 3.10 ou superior e execute:

```bash
git clone https://github.com/LuquinhasBohrer/e2ps-manual-builder.git
cd e2ps-manual-builder
python -m pip install -r requirements.txt
python main.py
```

No Windows, se `python` não for reconhecido, use `py` no lugar de `python`.

### Gerar uma nova distribuição Windows

Instale **Python 3.10+ de 64 bits** e **Inno Setup 6**. Em seguida, execute:

```bat
packaging\build_windows.bat
```

O executável portátil será criado em `dist\E2PS Manual Builder` e o instalador em `release`.

---

## Estrutura do código

| Componente | Responsabilidade |
|:--|:--|
| `main.py` | Inicialização do aplicativo, tema salvo e abertura direta de projetos `.e2ps`. |
| `main_window.py` | Interface principal, seções, páginas, IA, aparência e ações de projeto. |
| `styles.py` | Stylesheets E2PS para os temas Light e Dark e seleção do tema em tempo de execução. |
| `pdf_service.py` e `workers.py` | Renderização de PDF e tarefas de leitura em segundo plano. |
| `html_service.py` | Leitura de HTML/HTM e aproveitamento de texto e cabeçalhos. |
| `ai_service.py` e `translation_service.py` | Sugestões, chat, tradução e leitura visual de exceção. |
| `project_service.py` | Montagem do R Markdown e organização de ativos de exportação. |
| `project_file_service.py` | Leitura e gravação dos projetos `.e2ps`. |
| `packaging/` | Configuração do PyInstaller, Inno Setup e criação do instalador Windows. |

---

<div align="center">

### Segurança e boas práticas

Mantenha sua chave de IA em sigilo, confira números, unidades e referências técnicas antes de publicar um manual oficial e faça backup dos projetos `.e2ps` durante o trabalho.

**E2PS Manual Builder** · Estruture com clareza. Revise com critério. Exporte com segurança.

</div>
