# E2PS Manual Builder

O **E2PS Manual Builder** é uma aplicação desktop para montar manuais técnicos a partir de documentos PDF ou imagens individuais. O programa permite separar páginas e recortes, organizar o conteúdo em seções e subseções, inserir explicações entre figuras, trabalhar com IA e exportar um projeto estruturado em **R Markdown** para posterior compilação em PDF.

O fluxo foi concebido para manuais extensos e iterativos. Em vez de reconstruir o trabalho a cada sessão, o usuário pode salvar um projeto portátil com extensão **`.e2ps`**, reabri-lo posteriormente e continuar exatamente do ponto em que parou.

> O aplicativo auxilia na estruturação e na tradução técnica, mas o conteúdo gerado por IA deve ser revisado por uma pessoa qualificada antes da publicação de um manual oficial.

---

## Visão geral das funcionalidades

| Área | Recursos disponíveis |
|---|---|
| **Entrada de conteúdo** | Importação de PDFs, importação direta de múltiplas imagens, miniaturas e pré-visualização central de páginas. |
| **Edição visual** | Criação de múltiplos recortes independentes a partir da mesma página, seleção de imagem de capa e alteração da ordem do material nas seções. |
| **Estrutura do manual** | Criação, renomeação e edição de seções e subseções; inclusão de páginas e blocos de texto antes, entre ou depois de imagens. |
| **Assistente de IA** | Chat para perguntas sobre o documento, sugestão de estrutura baseada no texto disponível e geração de textos técnicos de apoio. |
| **Tradução** | Exportação multilíngue em português, inglês e espanhol; páginas podem ser preservadas como imagem ou convertidas em texto/tabelas editáveis. |
| **Exportação** | Geração de projeto R Markdown, cópia organizada de ativos, capa personalizada, sumário e estrutura pronta para compilação em PDF. |
| **Continuidade do trabalho** | Salvar e abrir projetos portáteis `.e2ps`, incluindo páginas, recortes, capa, estrutura e blocos de texto. |

---

## Requisitos

O aplicativo foi desenvolvido em Python e usa uma interface Qt. Para instalar e executar uma cópia local, é necessário ter **Python 3.10 ou superior** disponível no computador. A compilação final do R Markdown em PDF exige uma instalação funcional de R, Pandoc e uma distribuição LaTeX, mas esses componentes não são necessários para montar ou salvar o manual dentro do aplicativo.

| Dependência | Finalidade |
|---|---|
| `PySide6` | Interface gráfica desktop. |
| `PyMuPDF` | Leitura de PDFs, extração de páginas e texto. |
| `Pillow` | Abertura, conversão e criação de miniaturas de imagens. |
| `openai` | Comunicação com serviços compatíveis com a API OpenAI, como o GroqCloud. |

---

## Instalação e execução

Clone o repositório e instale as dependências no ambiente Python utilizado para iniciar o programa.

```bash
git clone https://github.com/LuquinhasBohrer/e2ps-manual-builder.git
cd e2ps-manual-builder
python -m pip install -r requirements.txt
python main.py
```

No Windows, caso o comando `python` não esteja disponível, substitua-o por `py`. Caso o programa seja iniciado por um arquivo `.bat`, execute-o a partir de um terminal para que uma eventual mensagem de erro permaneça visível.

```powershell
py -m pip install -r requirements.txt
py main.py
```

---

## Fluxo de trabalho recomendado

O fluxo abaixo reduz retrabalho e preserva a organização do manual durante a edição.

| Etapa | Procedimento |
|---|---|
| **1. Carregar o material** | Use **Open PDF** para converter as páginas de um PDF em itens do projeto ou **Open Images** para inserir imagens já preparadas. |
| **2. Preparar páginas** | Se necessário, use a ferramenta de recorte para criar quantas variantes forem necessárias de uma mesma página. Cada recorte é tratado como um item independente. |
| **3. Definir a capa** | Selecione uma imagem de capa para incluí-la automaticamente na exportação. |
| **4. Organizar o manual** | Crie seções e subseções, mova páginas entre elas e insira blocos de texto nos pontos que exigirem contexto técnico. |
| **5. Escolher o modo de cada página** | Defina se a página será mantida como imagem ou convertida para texto/tabela no projeto exportado. |
| **6. Salvar o trabalho** | Use **Save Project (.e2ps)** antes de fechar o aplicativo e sempre que concluir uma etapa relevante. |
| **7. Exportar** | Selecione os idiomas desejados e gere o projeto R Markdown. Revise o conteúdo antes da compilação final em PDF. |

---

## Estrutura, seções e blocos de texto

A árvore de conteúdo permite criar e editar seções e subseções após o carregamento das páginas. Os títulos podem ser renomeados, e o conteúdo pode ser reorganizado conforme a lógica do manual técnico.

Cada seção aceita uma sequência mista de blocos. Uma sequência pode conter, por exemplo, uma imagem, uma explicação textual, outra imagem e uma tabela reconstruída. Esse modelo é útil quando uma instrução precisa ser apresentada antes de uma figura ou quando é necessário explicar uma imagem entre duas etapas operacionais.

> Para manter a ordem desejada no PDF final, organize os blocos dentro de cada seção antes de iniciar a exportação.

---

## Assistente de IA e GroqCloud

O aplicativo aceita serviços compatíveis com a API OpenAI. O **GroqCloud** pode ser configurado na interface para o chat, sugestões de estrutura, textos de apoio e extração visual no modo Texto/Tabela.

Preencha os campos do painel de IA com a chave, a URL-base e o modelo disponibilizados pelo seu provedor. Para o GroqCloud, a URL-base normalmente utilizada é:

```text
https://api.groq.com/openai/v1
```

Após validar a configuração, clique em **Salvar Configs**. A chave, a URL-base e o modelo serão reutilizados automaticamente nas próximas aberturas do aplicativo no mesmo computador e perfil de usuário.

| Situação | Orientação |
|---|---|
| **Erro 401 — chave inválida** | Confirme se a chave pertence ao provedor configurado e se foi copiada integralmente. |
| **Erro 404 — modelo inexistente** | Se estiver usando GroqCloud, selecione um modelo disponível nesse provedor; modelos `gpt-*` não pertencem automaticamente ao catálogo do Groq. |
| **Erro 413 — requisição muito grande** | Reduza a quantidade de texto analisada, divida o material em etapas ou aguarde a renovação do limite do provedor. |
| **Exportação lenta** | A conversão de páginas em Texto/Tabela envia cada imagem separadamente ao modelo visual. Para grandes volumes, a demora é esperada; o progresso percentual informa o andamento. |

A disponibilidade, os modelos aceitos e os limites de uso dependem da conta e das políticas do provedor de IA escolhido. O aplicativo não inclui créditos de serviços externos.

---

## Tradução e modos de exportação

Cada página possui um modo de exportação independente. A escolha deve considerar o tipo de conteúdo técnico apresentado.

| Modo | Uso recomendado | Resultado no projeto R Markdown |
|---|---|---|
| **Imagem** | Diagramas, símbolos, certificados, desenhos, figuras com pouco texto ou páginas cujo layout deve ser preservado. | Copia a imagem original para o projeto, sem inserir respostas brutas ou textos internos da IA sobre a figura. |
| **Texto/Tabela (OCR)** | Tabelas de especificação, listas de parâmetros, avisos e conteúdos predominantemente textuais. | Solicita extração estruturada e tradução ao modelo visual; o conteúdo é inserido como texto ou tabela Markdown editável. |

O modo **Texto/Tabela (OCR)** é indicado para tabelas técnicas que precisam estar em português e permanecer legíveis na versão final. Como qualquer processo de OCR ou IA, números, unidades, referências normativas, símbolos e valores críticos devem ser revisados antes de publicar o manual.

Se a extração de uma página falhar, o projeto preserva a imagem original em vez de exportar uma mensagem de erro para o arquivo `.Rmd` ou para o PDF.

---

## Salvar e reabrir projetos `.e2ps`

O formato **`.e2ps`** é o formato oficial de projeto do E2PS Manual Builder. Ele é um arquivo portátil que reúne os recursos necessários para retomar o trabalho em outro momento ou em outro computador.

Um projeto `.e2ps` inclui as páginas e imagens importadas, miniaturas, recortes, imagem de capa, seções, subseções, blocos textuais, ordem dos conteúdos, idiomas selecionados e modo de exportação de cada página.

| Ação | Como usar |
|---|---|
| **Salvar projeto** | Clique em **Save Project (.e2ps)**, escolha uma pasta e informe o nome do arquivo. A extensão `.e2ps` é adicionada automaticamente. |
| **Abrir projeto** | Clique em **Open Project (.e2ps)** e escolha o arquivo salvo. A aplicação restaura os elementos editáveis e permite continuar a montagem. |
| **Projetos anteriores** | Arquivos legados `.emb` ainda podem ser abertos para evitar perda de trabalho. Ao salvá-los novamente, o formato será `.e2ps`. |

> A API Key de IA não é incluída no arquivo `.e2ps`. Assim, o projeto pode ser compartilhado sem enviar a credencial junto. A configuração permanece somente no perfil local do computador em que foi salva.

---

## Exportação R Markdown e PDF

A exportação gera uma pasta de projeto organizada por idioma, com o arquivo `.Rmd`, recursos visuais e referências necessárias para compilar o manual. O conteúdo pode ser exportado em português, inglês e espanhol conforme a seleção da interface.

Para converter o R Markdown em PDF, abra o arquivo `.Rmd` em uma instalação de RStudio ou execute a renderização por R com as dependências adequadas. A imagem de capa escolhida no aplicativo é copiada automaticamente para a estrutura exportada.

```r
rmarkdown::render("manual.Rmd")
```

A renderização pode exigir pacotes R adicionais, Pandoc e uma distribuição LaTeX. Esses requisitos pertencem ao ambiente de compilação do R Markdown e são independentes da instalação do aplicativo Python.

---

## Resolução de problemas

| Sintoma | Causa provável | Solução recomendada |
|---|---|---|
| O programa abre o terminal e fecha imediatamente. | Dependência ausente ou erro na inicialização. | Execute `python main.py` pelo terminal e instale novamente as dependências com `python -m pip install -r requirements.txt`. |
| O botão **Open Images** não processa arquivos. | Pillow não instalado no mesmo ambiente Python do aplicativo. | Execute `python -m pip install Pillow`. |
| As miniaturas ou a pré-visualização não aparecem. | Arquivo de origem inacessível, corrompido ou formato não suportado. | Reabra o PDF ou as imagens e confirme que os arquivos originais continuam disponíveis. |
| A exportação fica lenta. | Páginas em Texto/Tabela estão sendo analisadas individualmente pela IA. | Aguarde o progresso, exporte em etapas ou deixe diagramas e figuras no modo Imagem. |
| A pasta de exportação foi criada, mas ainda está sem imagens. | A exportação está em andamento ou uma análise visual está demorando. | Aguarde a conclusão; as páginas são copiadas antes da análise de IA nas versões atuais. |
| O PDF exportado contém conteúdo em idioma original. | A página foi mantida no modo Imagem ou a extração estruturada não foi revisada. | Use Texto/Tabela para material textual e revise o `.Rmd` antes da compilação. |
| O projeto não abre. | Arquivo inválido, corrompido ou não pertencente ao E2PS Manual Builder. | Tente abrir uma cópia de segurança e mantenha arquivos `.e2ps` em uma pasta local confiável. |

---

## Arquitetura do projeto

| Módulo | Responsabilidade |
|---|---|
| `main.py` | Ponto de entrada da aplicação desktop. |
| `manual_builder/main_window.py` | Janela principal, navegação, páginas, seções, configurações de IA e ações de projeto. |
| `manual_builder/models.py` | Modelos de páginas, seções e subseções. |
| `manual_builder/pdf_service.py` | Leitura de PDFs, renderização de páginas e extração de texto. |
| `manual_builder/crop_dialog.py` | Interface de seleção e geração de recortes de páginas. |
| `manual_builder/ai_service.py` | Chat, sugestões de estrutura e geração de textos com IA. |
| `manual_builder/translation_service.py` | Tradução textual, análise visual e extração estruturada de conteúdo. |
| `manual_builder/project_service.py` | Geração da estrutura R Markdown e cópia de ativos para exportação. |
| `manual_builder/export_worker.py` | Processamento de exportação em segundo plano e comunicação de progresso. |
| `manual_builder/project_file_service.py` | Leitura e gravação dos projetos portáteis `.e2ps`. |
| `manual_builder/workers.py` | Tarefas em segundo plano para carregamento de documentos e páginas. |
| `manual_builder/styles.py` | Estilos visuais da interface Qt. |

---

## Testes de persistência

O repositório contém um teste local para o fluxo de projeto. Ele verifica a criação e a reabertura de um arquivo `.e2ps`, incluindo páginas, recortes, capa, blocos de texto e preferências de IA.

```bash
python test_project_persistence.py
```

---

## Segurança e boas práticas

Mantenha a API Key em sigilo e nunca a publique em repositórios, arquivos compartilhados ou capturas de tela. O E2PS Manual Builder não grava a chave no `.e2ps`, mas a persistência local está vinculada ao perfil de usuário do sistema operacional. Evite usar a mesma conta local em computadores compartilhados.

Faça cópias de segurança periódicas dos seus arquivos `.e2ps`, especialmente antes de realizar grandes reorganizações ou substituir páginas e recortes. Para manuais críticos, mantenha também os PDFs e imagens de origem em uma pasta organizada.

---

## Licença

Desenvolvido para apoiar a padronização e a preparação de manuais técnicos da E2PS.
