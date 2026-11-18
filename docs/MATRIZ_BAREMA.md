# Matriz de aderência ao barema — Parte 2

**Importante:** `planejado` não é `implementado e testado`. Use `docs/ACEITE.md` como evidência final.

| Critério | Peso | Implementação enxuta | Evidência exigida | Atenção |
|---|---:|---|---|---|
| Elegibilidade | obrigatório | 2 APIs + Worker + Python, HTTP/WS/AMQP, Compose + README | `docker compose ps`, logs de serviços e execução em clone limpo | processos distintos ligados por rede |
| C1 Comunicação | 1,5 | REST/OpenAPI Node/Python + WS + RabbitMQ | consulta CLI e alteração visível via evento, reconexão | evitar polling contínuo |
| C2 Concorrência/escala | 1,5 | PostgreSQL lock/UNIQUE + 2 APIs + Traefik | burst de 50–100, sem números duplicados, balanceamento | autoscaling automático **não está previsto** |
| C3 Resiliência | 1,5 | outbox, retry/backoff, mensagens idempotentes, DLQ, falha parcial | parar API/Worker/RabbitMQ e recuperar; DLQ | Circuit Breaker exige implementação **real** para alegar excelência |
| C4 Nomes | 1,0 | Docker DNS + service discovery Traefik | resolução por nome, remoção/entrada de réplicas | não afirmar K8s/Consul ou algoritmo por latência |
| C5 Segurança | 1,0 | JWT + RBAC + TLS + `.env` + AWS Secrets Manager mínimo | 401/403, TLS, AWS `GetSecretValue` se autorizado | requisito específico Equipe 4 menciona Secrets Manager |
| C6 Logs | 1,0 | logs JSON + correlation ID | mesmo ID visto em API e Worker (Dozzle/logs) | erro inválido pode não atravessar Worker |
| C7 DevOps | 1,0 | Compose + CI GitHub + Terraform mínimo | clone limpo, build/testes CI, plan (apply só autorizado) | não alegar pipeline rodando antes do GitHub |
| C8 Live Demo | 1,5 | CLI, scripts e perguntas individuais | 3 testes de bancada ensaiados | docente aplica pelo menos 2 |

## Feedback específico da Equipe 4 (Parte 1)
- Por que Python cliente e Node API? -> interoperabilidade prevista no enunciado REST/OpenAPI.
- Qual fila? -> RabbitMQ; documentar exchange, fila, DLQ e fanout (ver `docs/ARQUITETURA_ALVO.md`).
- Credenciais? -> `.env` e integração mínima Secrets Manager (condicionada a autorização).
- Por que não só endpoint? -> WebSocket e processamento por eventos.
- DNS e tolerância a falhas foram pontos frágeis na Parte 1: exigir testes práticos.

## Divergências nos documentos acadêmicos
- A matriz textual converte base 10 por **0,3** para 3,0 pontos, mas a ficha posterior menciona **0,4**; confirmar regra final com docente.
- O exemplo antigo apresenta rubrica de 4,0 pontos distinta da matriz C1–C8; para Parte 2 usar principalmente C1–C8, preservando integração Node/Python.
- O exemplo antigo menciona squads 3–4; Parte 1 lista Equipe 4 com cinco. Não presumir que há autorização permanente sem confirmação.

## Itens que podem atingir apenas nível Bom sem trabalho extra
C2 não prevê HPA/ASG automático; C4 usa service discovery Docker/Traefik em lugar de Consul/Kubernetes; C5 não usa VPC isolada/mTLS; C6 usa agregação simples sem stack Grafana completa. Seja transparente na apresentação.
