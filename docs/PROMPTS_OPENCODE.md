# Prompts prontos — OpenCode + DeepSeek

## Regras de sessão
- Abrir OpenCode **na raiz do projeto**; selecionar DeepSeek usando `/models` e conferir provider disponível.
- `AGENTS.md` contém instruções persistentes; estas tarefas complementam, não substituem.
- Ideal: uma conversa por etapa F0–F6, mantendo `docs/PROGRESSO.md` como memória factual dos resultados.
- **Não colar segredos** no chat ou ferramenta. Não pedir à IA que invente resultado de teste.

## Prompt 0 — primeiro prompt (auditoria, SEM REESCRITA)
```text
Você é engenheiro de software responsável por entregar um TDE de Sistemas Distribuídos. Leia integralmente AGENTS.md, docs/PRD.md, docs/MVP.md, docs/ARQUITETURA_ALVO.md, docs/MATRIZ_BAREMA.md, docs/PLANO_EXECUCAO.md, docs/ACEITE.md, openapi.yaml, compose.yaml e os arquivos relevantes do código existente.
MISSÃO: executar somente a F0 — auditoria e baseline. NÃO reescreva nem recrie o projeto. Compare requisitos com código e testes reais; identifique inconsistências e dependências quebradas. Rode apenas verificações possíveis no ambiente. Produza tabela por requisito: implementado, comprovado, não testado, ausente ou defeituoso, com arquivo/linha e evidência de comando. Atualize somente docs/PROGRESSO.md e, se necessário, uma lista curta de bugs. Termine com a próxima tarefa de menor escopo e maior impacto. Nunca declare testes não executados como aprovados.
```

## Prompt por fase (substituir FASE e OBJETIVO)
```text
Execute exclusivamente a [FASE] descrita em docs/PLANO_EXECUCAO.md, considerando os defeitos documentados em docs/PROGRESSO.md. OBJETIVO: [OBJETIVO]. Antes de editar, identifique os arquivos e a causa precisa. Preserve openapi.yaml, compatibilidade Python/Node, schema de banco e escopo congelado do docs/MVP.md. Faça o menor diff que resolva o problema; não introduza pacotes, serviços ou arquitetura sem justificar. Rode os testes correspondentes; reporte comando, código de saída e resultado verdadeiro. Atualize docs/PROGRESSO.md com o que foi validado, o que falta e próximo passo. Pare após concluir esta fase, sem iniciar etapas futuras.
```

## Prompt de revisão independente (após cada fase)
```text
Revise o git diff da fase concluída como auditor de TDE. Compare AGENTS.md, PRD, MVP, openapi.yaml e critérios C1–C8. Procure regressões, alterações desnecessárias, segredos, promessas falsas, inconsistência de payload, falhas de concorrência e comportamento de rede. Não implemente features novas. Entregue lista priorizada: BLOQUEADOR / IMPORTANTE / MELHORIA OPCIONAL. Para cada item, dê arquivo/linha, cenário reproduzível, correção mínima e teste necessário. Só faça alterações se forem defeitos bloqueadores comprovados.
```

## Prompt de preparação para banca (apenas após testes)
```text
Usando exclusivamente docs/ACEITE.md, docs/PROGRESSO.md, logs e código atual, monte apresentação de 10 a 15 minutos, com demonstração dos fluxos, 3 testes de bancada, perguntas difíceis e respostas tecnicamente corretas. Identifique claramente qualquer critério não comprovado e limites do protótipo. Não atribua nota provável e não invente resultados.
```

## Formato obrigatório da resposta da IA
1. Objetivo da etapa e critérios C1–C8.
2. Diagnóstico/arquivos afetados.
3. Mudanças feitas (resumo do diff).
4. Testes executados com comandos e resultado real.
5. Pendências, riscos e próximo passo único.
