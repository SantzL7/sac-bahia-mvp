# MVP — Escopo técnico congelado

## Missão
Entregar **um sistema distribuído mínimo, executável e demonstrável**, não uma aplicação comercial. Se uma funcionalidade não comprova requisito do barema ou fluxo indispensável, **não implementar**.

## Componentes (somente estes)
1. `cliente-python/`: CLI `requests` + `websocket-client`.
2. `api/`: API REST Node.js/Express + endpoint WebSocket; 2 réplicas do mesmo serviço.
3. `database/`: PostgreSQL; postos, filas, guichês, senhas, eventos (outbox), eventos_processados.
4. `worker/`: publica outbox com confirmação, processa eventos com deduplicação e fanout.
5. `rabbitmq`: exchanges, fila de processamento, DLQ e notificações para APIs.
6. `traefik`: HTTPS/WSS, descoberta e balanceamento Docker.
7. `logs` Dozzle **somente perfil de observabilidade**, usado quando necessário para Tracing Audit.
8. `infra/terraform`: somente recurso mínimo de AWS Secrets Manager, condicionado a autorização.

## Funcionalidades mínimas
- Listar postos; consultar fila/ETA; emitir senha NORMAL/PRIORITARIA; consultar senha; chamar e finalizar; acompanhar WS.
- Login **somente atendente de demonstração**, com escopo de posto.
- Sequência de estados `AGUARDANDO > CHAMADA > FINALIZADA`.
- Identidade do cidadão = JWT escopado ao ticket devolvido na emissão; sem cadastro completo.
- Idempotência na emissão; lock transacional na emissão e na chamada; eventos persistidos na mesma transação.
- Mensagem `SENHA_EMITIDA`, `SENHA_CHAMADA`, `SENHA_FINALIZADA`.

## Rotas concretas já previstas no projeto
- `GET /health/live`, `GET /health/ready`
- `GET /api/v1/postos`, `GET /api/v1/postos/{id}/fila`
- `POST /api/v1/auth/atendente`
- `POST /api/v1/postos/{id}/senhas`
- `GET /api/v1/senhas/{id}`
- `POST /api/v1/guiches/{id}/chamar`
- `POST /api/v1/senhas/{id}/finalizar`
- `GET /ws` (upgrade WebSocket; verificar implementação/contrato)

**Contrato autoritativo:** `openapi.yaml` para REST; verificar documentação WS em `docs/ARQUITETURA.md`. Nunca criar rota extra por preferência do modelo.

## Critérios de recusa de escopo
Rejeitar pedidos da IA para adicionar Redis, Kafka, Kubernetes, React, OAuth, novas tabelas sem necessidade, novas filas por categoria, banco NoSQL, telemetria externa, deploy AWS completo ou testes cosméticos. Mudanças permitidas apenas para corrigir erro comprovado, segurança concreta ou requisito C1–C8 ausente, com justificativa.

## Regra de desenvolvimento com DeepSeek
- Trabalhar **uma etapa de `docs/PLANO_EXECUCAO.md` por vez**.
- Antes de modificar, conferir arquivos existentes e descrever lacuna.
- Reutilizar código atual; não reescrever projeto do zero.
- Alterar poucos arquivos relacionados; executar verificação correspondente e mostrar resultado real.
- Testes não executados devem constar como `NÃO EXECUTADO`, jamais `PASSOU`.
- Documentar resultados em `docs/PROGRESSO.md`.

## Definição de pronto
Todos os itens P0 do `docs/ACEITE.md` passaram no ambiente do grupo, com evidências. Itens de excelência não provados não podem ser apresentados como implementados.
