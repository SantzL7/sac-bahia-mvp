# Roteiro de entrega, avaliação e apresentação

## Contexto do barema

O documento da Parte 2 define quatro condições de elegibilidade: 2+ nós autônomos via rede, execução reproduzível, comunicação por protocolos contratados e domínio técnico individual. Os critérios somam 10,0 (C1=1,5; C2=1,5; C3=1,5; C4=1; C5=1; C6=1; C7=1; C8=1,5). A matriz principal converte por fator 0,3 para 3,0 pontos, mas a ficha final do próprio documento mostra fator 0,4; confirmar com professor.

O documento anterior de exemplos (REST/OpenAPI/Swagger) especifica Node.js/Express e cliente Python/requests, com resposta JSON e campos `posto`/`tempo_espera_minutos`. Este MVP conserva isso. A avaliação da Parte 1 da Equipe 4 cobrou explicação Python versus Node, eventos em tempo real no lugar de polling, definição de fila/tópicos, DNS/tolerância a falhas e gestão de segredos.

## Matriz de rastreabilidade e aceitação

| Critério | Evidência e procedimento | Limitação declarada |
|---|---|---|
| **C1** | CLI Python REST, `openapi.yaml`, WebSocket, publicação via RabbitMQ, `scripts/websocket_test.py` | WebSocket não é persistência |
| **C2** | `docker compose ps api` mostra 2 nós; `scripts/burst.py` (60 simultâneas), `scripts/concurrent_calls.py` | Escala manual, sem HPA |
| **C3** | `scripts/chaos.py`, interrupção RabbitMQ, retry e `scripts/dlq.py` | Banco/gateway são pontos únicos |
| **C4** | Docker DNS `postgres`/`rabbitmq`, Traefik Docker provider e roteamento path para 2 APIs | Não há DNS externo nem roteamento por latência |
| **C5** | Provar TLS local, autenticação JWT, `scripts/security_test.py` (401/403) e `.env` ignorado; opcional leitura real Secrets Manager com `aws_secrets_loaded` | TLS cert não confiável e sem mTLS interno |
| **C6** | `scripts/tracing.py` vê mesmo Correlation ID nos dois processos, logs JSON/Dozzle | Não é tracing completo com spans/Prometheus |
| **C7** | Clone limpo, `python scripts/setup_env.py`, Compose, README, CI GitHub Actions, Terraform apenas segredo | Terraform AWS depende de permissão/custo |
| **C8** | Rodar três scripts do professor, explicar transação, escolha do broker, fallback e decisões | Demonstração ainda precisa ser ensaiada |

Os níveis **Excelente** do barema incluem características que este MVP não pretende cumprir integralmente (especialmente HPA/ASG, service discovery avançado e mTLS/VPC). Não prometer nota 10 como fato.

## Roteiro da demonstração (sugestão de 10 a 15 minutos)

1. Mostrar `docker compose ps` com gateway, postgres, rabbitmq, worker e **duas** APIs.
2. Mostrar `openapi.yaml`, consulta de postos e fila a partir do cliente Python.
3. Emitir senha, abrir WebSocket em outro terminal, obter login de atendente, chamar/finalizar; confirmar evento e mudança de estado.
4. Abrir logs API/Worker com um mesmo Correlation ID; observar exchanges e filas RabbitMQ Management.
5. Executar `burst.py` e `concurrent_calls.py`; explicar bloqueio transacional, índices UNIQUE e idempotência.
6. Executar `chaos.py`; mostrar Traefik roteando pela segunda réplica e reinicialização.
7. Executar `dlq.py` e, se possível, falha/reconexão de RabbitMQ mostrando o Circuit Breaker e eventos em outbox.
8. Mostrar `.env.example` sem segredos, RBAC e opção AWS Secrets Manager; concluir com limitações.

## Divisão sugerida de responsabilidades

| Papel | Entrega técnica e explicação |
|---|---|
| Pessoa 1 — API | REST/OpenAPI, middleware, integração Python/Node |
| Pessoa 2 — Banco | Modelo SQL, transações, locks, idempotência |
| Pessoa 3 — Eventos | Worker, RabbitMQ, retries, DLQ, WebSocket |
| Pessoa 4 — Infra | Compose, Traefik, DNS, CI, carga e caos |
| Pessoa 5 — Segurança e demo | JWT/RBAC, Secrets Manager, logs, arguição |

Atribuições devem ser adaptadas aos integrantes reais; **todos precisam entender o fluxo completo** para a nota individual. O documento de exemplos anterior menciona squads de 3–4, mas a Equipe 4 tinha cinco na Parte 1: confirmar elegibilidade com o professor.

## Checklist de aceite — não declarar como realizado até testar

- [ ] Repositório hospedado no GitHub, com commits e README.
- [ ] Primeira subida num computador diferente funciona via Compose.
- [ ] API em duas réplicas comunicando-se apenas por rede com DB/Worker/broker.
- [ ] Cliente Python realiza fluxo de usuário e atendente; contrato corresponde a JSON real.
- [ ] WebSocket recebe eventos sem polling contínuo; reconcilia após reconectar.
- [ ] 60 emissões simultâneas sem duplicações; chamadas concorrentes sem conflito.
- [ ] Repetição de Idempotency-Key retorna mesmo id; payload divergente retorna 409.
- [ ] Evento em outbox sobrevive à indisponibilidade temporária do RabbitMQ.
- [ ] Retry e DLQ demonstrados; Circuit Breaker tem transição OPEN/HALF_OPEN/CLOSED comprovada.
- [ ] Queda de uma API não derruba consultas; sistema sinaliza corretamente falha de banco/gateway.
- [ ] Token de cidadão não acessa outra senha; atendente de posto 1 não acessa posto 2.
- [ ] Logs API/Worker compartilham Correlation ID; console local acessível.
- [ ] TLS local comprovado, suas limitações explicadas; segredos não aparecem no Git.
- [ ] Caso se alegue AWS Secrets Manager, acesso real comprovado com IAM mínimo.
- [ ] CI passa no GitHub; Terraform é validado se apresentado.
- [ ] Testes repetidos antes da arguição e capturas de evidência sem credenciais.

## Códigos e evidências para registrar

Guardar print de `docker compose ps`, vídeo curto/print do CLI+WS, saída de `burst.py` e `chaos.py`, logs correlacionados de `tracing.py`, print de DLQ no Rabbit Management, print de workflow verde no GitHub. Registrar problema conhecido e sua limitação; **não falsificar execução**.
