# Plano de mudança — Manual de Componentes e Manual Operacional

## 1. Objetivo

Adicionar ao E2PS Manual Builder a possibilidade de escolher entre dois tipos de manual antes ou durante a montagem do projeto: **Manual de Componentes**, que preservará o fluxo e o template atuais, e **Manual Operacional dos Equipamentos**, que utilizará o layout, os metadados e a estrutura editorial exemplificados em `E2SOLID.Rmd` e `E2SOLID.pdf`.

A entrega deverá manter a instalação Windows existente, preservar a abertura de projetos `.e2ps` antigos e gerar uma nova versão do instalador pelo mesmo pipeline atual de PyInstaller, Inno Setup e GitHub Actions.

## 2. Diagnóstico da implementação atual

O repositório é uma aplicação desktop em Python com PySide6. O estado do trabalho é mantido em objetos `PdfPage`, `ManualSection` e `ManualSubsection`; a persistência ocorre em um arquivo `.e2ps`, que é um ZIP com `project.json` e os ativos de páginas, miniaturas e capa. A exportação é centralizada em `manual_builder/project_service.py`, que hoje utiliza um único template R Markdown genérico e pode criar pastas por idioma. A geração efetiva do PDF fica a cargo do ambiente R Markdown/RStudio do usuário.

O instalador atual é construído por `packaging/build_windows.bat`, empacotado pelo PyInstaller e compilado pelo Inno Setup. O workflow `.github/workflows/windows-installer.yml` publica o instalador quando uma tag `v*` é criada. O tipo de manual ainda não existe no modelo, na interface, no manifesto `.e2ps` ou no exportador.

## 3. Diferenças do manual operacional de referência

O manual operacional de referência não é apenas uma variação de título. Ele possui um template editorial próprio, com capa específica, logo e rodapé da E2PS, `lualatex`, fonte Gotham Rounded Book, sumário, índice de figuras, estilos de títulos em laranja e posicionamento controlado de figuras. A capa contém o texto “Manual Operacional”, o nome do equipamento, a imagem principal, a data de publicação e a revisão.

A estrutura observada é composta por um prefácio com dados do fabricante e do equipamento, instruções de segurança, sistema de controle, capítulo do equipamento e uma seção final destinada às informações e imagens específicas do equipamento. O Rmd de referência marca os capítulos 2 e 3 como bloco protegido editorialmente, enquanto o capítulo 4 é variável; na implementação do Builder, todos esses conteúdos serão carregados como base em português e permanecerão editáveis. O corpo utiliza texto técnico e várias figuras com legendas e tamanhos individuais, e o PDF final tem 37 páginas no exemplo E2SOLID.

## 4. Solução proposta

### 4.1 Seleção do tipo de manual

Adicionar um campo **Tipo de manual** na área de metadados da janela principal, com duas opções:

| Tipo | Identificador interno | Comportamento |
|---|---|---|
| Manual de Componentes | `components` | Mantém o template e o fluxo atuais, sem alteração de comportamento para usuários existentes. |
| Manual Operacional dos Equipamentos | `operational` | Usa o template operacional, os campos adicionais e a organização específica do equipamento. |

O tipo deverá ser escolhido ao iniciar um novo manual e poderá ser alterado enquanto o projeto estiver vazio. Quando o projeto já possuir conteúdo, a alteração deverá solicitar confirmação e explicar que o modo de exportação e os campos de capa podem mudar. A implementação deverá evitar perda silenciosa de dados; se a troca exigir limpeza de campos incompatíveis, isso será informado antes da ação. A nova entrega será publicada como **E2PS Manual Builder V3**, preservando a abertura de projetos legados da V1/V2.

### 4.2 Campos específicos do Manual Operacional

Quando o tipo operacional estiver selecionado, a interface deverá exibir campos adicionais e ocultar ou renomear campos que pertencem somente ao formato atual:

| Campo | Uso no Rmd/PDF |
|---|---|
| Nome/título do equipamento | Capa e título do manual, por exemplo, E2SOLID. |
| Tipo do equipamento | Campo “Tipo” do capítulo de prefácio. |
| Modelo | Campo “Modelo” do capítulo de prefácio. |
| Número de série / ano de fabricação | Campo de identificação do equipamento. |
| Revisão | Texto exibido na capa; será separado da data de publicação. |
| Data de publicação | Mês/ano exibido na capa e no documento. |
| Imagem principal do equipamento | Imagem central da capa operacional. |
| Conteúdo específico do capítulo 4 | Conjunto fixo de campos editoriais para funcionamento, características e funções do equipamento; os campos serão editáveis. |
| Conteúdo/imagens da seção final “EQUIPO” | Área variável, com padrões de blocos e subseções, que o usuário poderá expandir, editar e reorganizar conforme a necessidade. |

Os campos deverão ser salvos no `.e2ps`, restaurados ao abrir o projeto e incluídos no nome dos placeholders do template. O modo de componentes continuará utilizando os campos atuais sem exigir os campos operacionais. A base inicial do manual operacional será fornecida em **português**, inclusive para os capítulos 1, 2 e 3; todo o conteúdo permanecerá editável na interface, sem bloqueio editorial permanente.

### 4.3 Template e exportação

Separar o exportador em duas estratégias explícitas, mantendo o template atual para `components` e criando um template operacional para `operational`. O novo template deverá ser mantido como arquivo versionado no repositório, em vez de permanecer como uma string extensa dentro do código Python. Isso facilitará revisão editorial, atualização do layout e comparação com o `E2SOLID.Rmd` de referência.

O template operacional terá três partes:

1. **Cabeçalho e configurações LaTeX/HTML**, contendo os pacotes, fonte, estilos, cabeçalho, rodapé, sumário e índice de figuras.
2. **Conteúdo-base editável**, contendo o prefácio padrão, as instruções de segurança e a estrutura-base do sistema de controle. Esses trechos serão carregados em português, mas poderão ser revisados e editados pelo usuário antes da exportação.
3. **Conteúdo variável padronizado**, contendo o capítulo do equipamento, funções principais e blocos da seção final “EQUIPO”, gerados a partir dos textos, páginas, recortes e imagens montados na aplicação. A aplicação fornecerá modelos de bloco para manter uma aparência consistente, sem impedir a edição do conteúdo.

Para evitar uma limitação importante do arquivo recebido, as imagens do Rmd operacional não serão referenciadas por caminhos absolutos ou por uma pasta externa presumida. O usuário poderá adicionar imagens diretamente no Manual Builder, selecionar em quais partes do manual elas serão utilizadas e reposicioná-las dentro da composição da seção. Na exportação, todas as imagens serão copiadas para a pasta `img` do projeto, e os blocos R Markdown serão gerados com caminhos relativos.

O editor operacional deverá permitir uma composição visual de texto e imagem semelhante a um “arrasta e posiciona”. Cada bloco poderá conter texto, imagem ou ambos, com ordem, alinhamento, largura relativa, legenda e posição configuráveis. O objetivo é permitir que o usuário decida onde a caixa de texto fica em relação à imagem, sem obrigá-lo a aceitar sempre a sequência fixa “texto e depois figura”. A implementação deverá definir uma representação estável desses posicionamentos para que o resultado seja reproduzível no R Markdown e no PDF.

A exportação multilíngue continuará disponível para o modo operacional. O português será o idioma-base do conteúdo inicial e o exportador deverá gerar versões em **português, inglês e espanhol**. A tradução deverá abranger textos da base, campos do equipamento, capítulo 4, subseções, legendas e textos adicionados pelo usuário. Imagens serão reaproveitadas entre os idiomas, exceto quando o usuário optar por inserir uma versão específica para determinado idioma. Nomes técnicos, TAGs, códigos, unidades e identificadores deverão ser preservados por regras de tradução técnica e revisão do usuário.

### 4.4 Estrutura da interface de conteúdo

O editor atual de seções, subseções, páginas, recortes e blocos de texto será preservado. Para o modo operacional, a árvore deverá iniciar com uma estrutura sugerida ou com áreas editoriais identificadas, por exemplo:

- Prefácio / Dados do equipamento;
- Instruções de segurança;
- Sistema de controle;
- Equipamento;
- Conteúdo específico do equipamento.

A base dos capítulos será exibida já preenchida em português e será totalmente editável. A aplicação poderá oferecer uma ação para restaurar o texto-base de uma seção, mas não deverá impedir alterações. A seleção de páginas, recortes e imagens continuará sendo feita pelo fluxo atual; os itens destinados ao capítulo do equipamento e à seção final “EQUIPO” serão exportados conforme os blocos e padrões escolhidos pelo usuário.

A análise automática de estrutura continuará sendo editável. Para o modo operacional, ela deverá reconhecer que páginas de capa, sumário, índice de figuras e referências não devem ser duplicadas como conteúdo do capítulo variável, e deverá sugerir a classificação das demais páginas no capítulo específico do equipamento.

## 5. Modelo de dados e compatibilidade

Adicionar um campo de tipo ao metadata do projeto, com valor padrão `components` quando o campo estiver ausente. Os campos operacionais serão armazenados em uma seção própria do metadata, por exemplo `operational`, para não misturar dados do modo de componentes com dados da capa operacional.

A versão atual do formato `.e2ps` deverá continuar sendo aceita. A leitura de projetos antigos deverá aplicar migração em memória: se não houver `manual_type`, considerar `components`; se não houver campos operacionais, usar valores vazios. Para o V3, a escrita deverá registrar a versão do formato e o tipo de manual de forma explícita, com migração documentada para projetos V1/V2. A migração nunca deverá transformar automaticamente um projeto antigo de componentes em operacional.

O objetivo de compatibilidade é que um projeto antigo abra sem intervenção, continue exportando como Manual de Componentes e não perca páginas, recortes, textos, seções ou capa.

## 6. Arquivos que deverão ser alterados

| Área | Alteração prevista |
|---|---|
| `manual_builder/models.py` | Adicionar constantes/modelos auxiliares para tipo de manual e metadados operacionais, se necessário. |
| `manual_builder/main_window.py` | Campo de seleção do tipo, formulário operacional, troca de modo, validações, restauração e salvamento de metadata. |
| `manual_builder/project_file_service.py` | Persistência e migração dos novos campos, mantendo projetos legados. |
| `manual_builder/project_service.py` | Seleção de renderer/template, exportação operacional, assets, figuras, capa, rodapé, sumário e índice de figuras. |
| `manual_builder/export_worker.py` | Encaminhamento do tipo e dos metadados operacionais para o serviço de exportação em segundo plano. |
| `manual_builder/ai_service.py` e/ou lógica de estrutura | Regras específicas para não importar capa/sumário/índice como conteúdo operacional e sugerir o capítulo variável. |
| `manual_builder/assets/` | Templates, imagens padrão e eventualmente arquivos auxiliares do layout operacional. |
| `tests` existentes e novos testes | Cobertura do novo tipo, migração, template e exportação. |
| `README.md` | Documentação do seletor, campos operacionais, exportação e fluxo de build. |
| `packaging/` e workflow | Atualização de versão/nome do instalador e validação do pacote final. |

## 7. Plano de testes

Os testes serão implementados antes ou junto da funcionalidade, cobrindo o comportamento observável:

| Grupo | Verificações |
|---|---|
| Persistência | Salvar e reabrir projeto operacional; preservar tipo e todos os campos; abrir projeto legado como `components`. |
| Interface | Exibir/ocultar campos por tipo; restaurar valores; editar integralmente a base operacional; validar campos obrigatórios sem bloquear campos opcionais. |
| Templates | Verificar front matter, lualatex, logo, rodapé, sumário, índice de figuras, placeholders e ausência de caminhos absolutos. |
| Conteúdo | Garantir que páginas textuais sejam exportadas como texto, figuras como imagens e que os blocos de texto/imagem mantenham ordem, alinhamento, largura, posição e legendas. |
| Base editorial | Garantir que os capítulos-base sejam carregados em português e permaneçam totalmente editáveis, sem sobrescrita automática durante a tradução. |
| Exportação | Gerar pastas válidas em português, inglês e espanhol para o modo operacional e manter o comportamento atual do modo `components`. |
| Regressão | Executar os testes existentes de PDF, persistência, imagens, HTML, smoke test e instalador. |
| Empacotamento | Executar PyInstaller, conferir assets incluídos, instalar o `.exe` em Windows e abrir um projeto de cada tipo. |
| PDF | Compilar pelo menos um Rmd de componentes e um Rmd operacional em ambiente com R, Pandoc, LaTeX e os assets necessários; conferir capa, sumário, índice de figuras, rodapé e numeração. |

No ambiente atual, a suíte não foi executada porque `pytest` não está instalado. Isso será resolvido no ambiente de desenvolvimento/CI durante a implementação; a ausência do comando não representa falha funcional do código atual.

## 8. Build e instalador

A proposta aprovada é publicar a funcionalidade como **E2PS Manual Builder V3**. O instalador deverá receber uma nova identidade/versionamento V3, com diretório, AppId, atalhos e nome de release próprios para não sobrescrever nem conflitar com as instalações V1/V2. A versão semântica inicial poderá ser `3.0.0`.

O build continuará usando `packaging/build_windows.bat`. O script deverá incluir os novos templates e assets na especificação do PyInstaller. O Inno Setup deverá receber a nova versão, gerar um nome de arquivo correspondente e manter a associação `.e2ps`, os atalhos e o fechamento automático do aplicativo durante atualização.

O workflow do GitHub Actions deverá ser atualizado para publicar o nome dinâmico ou o novo nome fixo do instalador. A validação final deverá incluir o artefato portátil, o instalador, a instalação limpa, uma atualização sobre a V2 existente e a abertura por duplo clique de um `.e2ps`.

## 9. Critérios de aceite

A funcionalidade será considerada pronta quando o usuário puder criar um projeto novo, escolher **Manual de Componentes** ou **Manual Operacional**, preencher os campos correspondentes, montar o conteúdo, salvar e reabrir o `.e2ps`, exportar o Rmd e obter a estrutura correta sem alterar o comportamento de projetos antigos.

Para o modo operacional, o Rmd deverá conter o layout da referência: capa operacional, cabeçalho e rodapé E2PS, estilos, sumário, índice de figuras, campos de identificação, capítulos-base editáveis, capítulo variável do equipamento e seção final para conteúdo específico. O conteúdo variável deverá usar os assets internos da exportação, e não depender de uma pasta `Imagens` externa não fornecida ao projeto.

O instalável Windows deverá ser gerado pelo pipeline existente, conter os novos templates/assets e abrir corretamente em uma máquina Windows compatível sem exigir Python instalado.

## 10. Decisões recebidas para a implementação

As decisões recebidas foram incorporadas ao plano. O entendimento aprovado para a implementação é:

1. Os capítulos-base serão carregados em português, mas todo o manual será totalmente editável.
2. O capítulo 4 terá campos e estrutura fixa, porém com conteúdo editável.
3. A seção final “EQUIPO” será variável, expansível e baseada em padrões de blocos e subseções.
4. Texto e imagem poderão ser adicionados, posicionados e alinhados visualmente pelo usuário; as imagens irão para `img` na exportação.
5. O modo operacional terá tradução textual para português, inglês e espanhol, com português como base.
6. A nova distribuição será a versão V3, inicialmente com versionamento `3.0.0`.
7. As imagens serão adicionadas pelo próprio Manual Builder e selecionadas nas partes em que serão utilizadas; não haverá dependência obrigatória de uma pasta externa `Imagens/`.

## 11. Ordem de execução após aprovação

A implementação será feita em etapas: primeiro o modelo e a migração `.e2ps`; depois a seleção de tipo e os campos da interface; em seguida os templates e o renderer operacional; depois a integração com exportação multilíngue e análise de estrutura; por fim os testes, a documentação, o build Windows e a validação do instalador. Cada etapa será verificada antes da seguinte para reduzir risco de regressão no fluxo atual.
