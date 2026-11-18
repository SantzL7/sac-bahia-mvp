# Plano de execução orientado a OpenCode + DeepSeek

**Modo de uso:** rode a tarefa de cada fase separadamente; NÃO dê todas as fases para a IA implementar de uma vez. Ver `docs/PROMPTS_OPENCODE.md`. O código-base já existe. A primeira ação é auditoria do que existe, não gerar tudo novamente.

## F0 — Auditoria e baseline (primeira ação, bloqueante)
- Ler `AGENTS.md`, `docs/PRD.md`, `docs/MVP.md`, `openapi.yaml`, `compose.yaml`, `database/*.sql`, API, Worker, CLI e scripts.
- `npm run check`, `npm test`, `python -m compileall -q cliente-python scripts`, `docker compose config -q` (configurar `.env` local antes), se ferramentas disponíveis.
- Criar tabela status `EXISTE / FUNCIONA TESTADO / QUEBRADO / NÃO TESTADO / FALTA` por requisito.
- Identificar diferenças reais do contrato, risco de segredos, problemas de inicialização, WS, RabbitMQ e logs.
- **Entrega:** diagnóstico objetivo em `docs/PROGRESSO.md`. Nesta fase não reescrever arquivos amplamente.

## F1 — Núcleo e contrato (C1)
- Corrigir divergências encontradas entre `openapi.yaml`, REST e CLI.
- Garantir lista de postos, consulta de fila, emissão, consulta senha, login atendente, chamada e finalização.
- Verificar retornos 400/401/403/404/409 e campos `posto` e `tempo_espera_minutos`.
- **Aceite:** smoke test E2E real. Não iniciar F2 enquanto base falha.

## F2 — Consistência e concorrência (C2/C3)
- Validar transações, lock de `filas`, `UNIQUE`, chave idempotente e atomicidade do evento.
- Rodar testes de 60 concorrentes, chamadas simultâneas e repetição de chave.
- **Aceite:** nenhum número duplicado, nenhuma dupla chamada, 409 para chave conflitante, rollback em falha.

## F3 — Eventos e WS (C1/C3)
- Conferir `eventos`/outbox, publicação confirmada, consumo idempotente, RabbitMQ e DLQ.
- Garantir fluxo real mudança -> publicação -> processamento -> fanout -> duas APIs -> WS cliente.
- Testar reconexão e restauração REST, sem polling HTTP periódico.
- **Aceite:** evento transmitido após chamada e finalização, broker parado sem perda de senha.

## F4 — Gateway, segurança e telemetria (C4/C5/C6)
- Verificar 2 réplicas por Traefik, TLS/WSS, health checks, descoberta Docker e failover de API.
- Verificar JWT, papel/escopo de posto, validação de entrada, ausência de segredos no Git.
- Verificar logs JSON e `correlation_id` ao longo do fluxo. Verificar se existe Circuit Breaker real; se não, registrar gap priorizado e decidir implementação mínima para C3 excelente.
- **Aceite:** scripts security, chaos e tracing; screenshots/logs sem credenciais.

## F5 — Automação e serviço de segredos (C5/C7)
- Garantir `.env.example`, script `setup_env.py`, Compose e CI realmente executando.
- Gerar lockfile `package-lock.json` e versioná-lo; preferir `npm ci` no CI/contêiner se compatível.
- AWS somente com autorização: `terraform fmt/validate/plan`, leitura real do segredo com permissão mínima; não executar apply sem custo aprovado.
- **Aceite:** clone limpo e CI verde; evidência real AWS ou bloqueio explícito.

## F6 — Homologação, entrega e arguição (C8)
- Ensaiar `smoke.py`, `burst.py`, `concurrent_calls.py`, `websocket_test.py`, `chaos.py`, `tracing.py`, `dlq.py`.
- Preparar cenário com duas APIs, monitor de logs e cliente Python, inclusive sem internet na sala.
- Registrar comandos, data, resultado, captura de tela e limitações.
- Distribuir explicação de fluxos por todos os integrantes. Criar tag Git da versão final somente após validação.
- **Aceite:** checklist `docs/ACEITE.md` integralmente revisado; nenhum teste mentiroso.

## Regras em caso de atraso
Priorizar F0–F3, depois roteamento/segurança/logs e testes de caos. AWS não bloqueia a demonstração local, mas pode afetar a avaliação de C5 e precisa ser reportada como pendência se não integrada. **Nunca remover a comunicação em tempo real, transações ou testes C8 para criar frontend.**
