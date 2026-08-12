# Relatório Final - Otimização de Tokens da IA (E2PS Manual Builder)

O repositório `https://github.com/LuquinhasBohrer/e2ps-manual-builder.git` foi atualizado para resolver o erro `413 Rate Limit Exceeded` (Tokens Per Minute - TPM) ao solicitar sugestão de estrutura:

1. **Otimização de Contexto e Truncamento Inteligente**:
   - O serviço de IA (`ManualAIService`) foi refatorado para limitar o envio de trechos de texto por página (amostragem inteligente de até 30 páginas e truncamento de trechos para no máximo 128 caracteres).
   - O histórico de chat foi limitado a uma janela deslizante (últimas 6 mensagens), evitando o crescimento excessivo de tokens acumulados.
   - O parâmetro `max_tokens` foi delimitado explicitamente (`600` para sugestões e `400` para geração de texto técnico).

2. **Sincronização com o GitHub**:
   - A otimização foi testada e enviada (*commit and push*) com sucesso para o repositório oficial no GitHub.
