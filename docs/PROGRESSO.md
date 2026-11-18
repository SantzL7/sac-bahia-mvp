# Progresso factual do MVP

**Última atualização:** 2026-11-18 | **Situação:** F1 (REST/contrato), F2 (consistência/concorrência), F3 (eventos/WS) e F4 (gateway/segurança/telemetria) validadas em execução real. Balanceamento 10/10 entre réplicas, failover com nova emissão durante a queda, JWT/TLS/WSS, circuit breaker, DLQ e agregação Dozzle passaram. CI/Git, AWS Secrets Manager e ensaio final da demo continuam pendentes.

## 0. Estado atual do ambiente

- Docker Desktop iniciado; `docker info` responde.
- `.env` local criado por `py scripts/setup_env.py --quiet` (conteúdo não versionado).
- `.venv` criado com `requests`, `websocket-client` e validador OpenAPI.
- Stack em execução: PostgreSQL, RabbitMQ, Traefik, Worker e **2 réplicas da API**.
- Volumes criados; nenhum `docker compose down -v` foi executado.
- Dados de demonstração foram gerados pelos smokes; o banco não é um ambiente limpo.
- Durante a F2 e a F3 o Docker Desktop parou sozinho mais de uma vez; foi reiniciado e a stack voltou com `docker compose up -d --scale api=2`. Volumes e dados foram preservados.
- Estado após a F4: 295 eventos, 0 pendentes no outbox e 0 sem registro em `eventos_processados`; 16 senhas AGUARDANDO, 132 CHAMADA e 5 FINALIZADA. `sac.events.dlq` contém 1 mensagem malformada injetada pelo teste de DLQ. Nenhuma constraint temporária permanece.
- Dozzle iniciado com `docker compose --profile observabilidade up -d logs` e exposto em `127.0.0.1:8081`; a stack passa a ter 7 containers (o profile não sobe por padrão).


## 1. Inventário real (não presumido)

- 50 arquivos de projeto, excluindo `node_modules` e `__pycache__`.
- Componentes presentes: `api/` (Node/Express + WS), `worker/` (outbox + consumidor), `cliente-python/`, `database/` (schema/seed), `shared/`, `scripts/`, `tests/`, `infra/terraform/`, `.github/workflows/`.
- Contratos/configuração presentes: `openapi.yaml`, `compose.yaml`, `compose.aws.yaml`, `Dockerfile`, `.env.example`, `.gitignore`, `.dockerignore`.
- Documentação presente: PRD, MVP, REQUISITOS, ARQUITETURA, ARQUITETURA_ALVO, MATRIZ_BAREMA, PLANO_EXECUCAO, ACEITE, ENTREGA, VALIDACAO_LOCAL, PROMPTS_OPENCODE, GUIA_OPENCODE.
- Artefatos agora presentes localmente: `.env`, `.venv`, `node_modules`.
- Artefatos ainda ausentes: `package-lock.json`, `.git`, `docs/evidencias/`.
- `node_modules` foi gerado com `npm install --no-package-lock`; é ignorado pelo `.gitignore`.

## 2. Comandos executados e resultado real

| Comando | Resultado |
|---|---|
| `npm run test:all` | **PASSOU** — análise sintática dos JS e 4 testes unitários (`tests/core.test.js`). |
| `py -m compileall -q cliente-python scripts` | **PASSOU** — sintaxe Python. |
| `npm install --no-package-lock --no-audit --no-fund` | **PASSOU** — 178 pacotes; aviso de depreciação transitiva `uuid@9.0.1`. |
| `node -e "require(...)"` para express, pg, ws, jsonwebtoken, amqplib, AWS SDK | **PASSOU** — dependências resolvidas. |
| `docker compose config -q` com variáveis temporárias válidas | **PASSOU** — sintaxe/estrutura do Compose. Sem variáveis, falha de propósito cobrando `.env`. |
| Parsing YAML de `compose.yaml`, `compose.aws.yaml`, `openapi.yaml`, CI | **PASSOU** — sintaxe YAML. |
| `docker info` | **F0 FALHOU** (daemon parado); **F1 PASSOU** após iniciar o Docker Desktop (`29.7.2`). |
| `terraform version` | **NÃO EXECUTADO** — Terraform não instalado. |
| `git status` | **FALHOU** — a pasta não é repositório Git. |
| Smokes REST/WS/RabbitMQ/PostgreSQL, burst, chaos, DLQ, tracing | **F0 NÃO EXECUTADOS**; **F1:** `smoke.py` e `security_test.py` com PASS; **F2:** `burst.py`, `concurrent_calls.py` e `consistency_test.py` com PASS; **F3:** `websocket_test.py`, `ws_flow_test.py`, `dlq.py`, `broker_chaos.py`, `ws_reconnect_test.py`, `cli_idle_test.py` e `tracing.py` com PASS; **F4:** `balancing.py`, `chaos.py` (ampliado), `security_test.py` (ampliado), `circuit_breaker_test.py`, `telemetry_test.py`, `secrets_check.py` e `tracing.py` com PASS. |
| AWS Secrets Manager (`terraform plan/apply`, `GetSecretValue`) | **NÃO EXECUTADO** — sem credenciais/custo autorizado; requisito permanece pendente. |

### F1 — execução real

| Comando | Resultado |
|---|---|
| `py scripts/setup_env.py --quiet` | **PASSOU** — `.env` criado; conteúdo não exibido. |
| `docker compose up -d --build --scale api=2` | **PASSOU** — imagens construídas, 6 serviços iniciados, exit 0. |
| `docker compose ps` | **PASSOU** — API-1 e API-2, Postgres, RabbitMQ e Worker `healthy`; Traefik `Up`. |
| `GET https://localhost:8443/health/ready` | **PASSOU** — HTTP 200, `database: ok`, `node` de uma réplica. |
| `python scripts/smoke.py` | **PASSOU** — REST, idempotência, RBAC, consulta, chamada e finalização. |
| `python scripts/security_test.py` | **PASSOU** — 401/403 e isolamento por ticket/posto após corrigir o guichê do teste. |
| CLI `postos` e `fila --posto 1` | **PASSOU** — lista 2 postos e retorna `posto`, `tempo_espera_minutos`, contagem e guichês. |
| Checagem de 400/401/403/404/409 | **PASSOU** — 13 cenários verificados, todos com o status esperado. |
| `openapi-spec-validator` em `openapi.yaml` | **PASSOU** — contrato válido em OpenAPI 3.0.3. |
| `npm run test:all` | **PASSOU** — sintaxe e 4 testes unitários. |
| `py -m compileall -q cliente-python scripts` | **PASSOU**. |
| `docker compose config -q` com `.env` | **PASSOU**. |
| `docker compose logs api worker` | **PASSOU** — logs JSON com `event_persisted`, `event_published` e `event_processed` correlacionados. |
| Consulta `SELECT id,posto_id FROM guiches` | **PASSOU** — guichês 1/3 no posto 1 e 2/4 no posto 2, confirmando a correção dos scripts. |

**Arquivos alterados na F1:** `openapi.yaml`, `scripts/security_test.py`, `scripts/concurrent_calls.py`, `docs/PROGRESSO.md` e `docs/ACEITE.md` (evidências pontuais). `scripts/concurrent_calls.py` foi corrigido, mas **não executado** nesta fase; a concorrência pertence à F2.

### F2 — execução real

| Comando / verificação | Resultado |
|---|---|
| `python scripts/burst.py` | **PASSOU** — 60 emissões simultâneas, 60 IDs e números únicos; exit 0; ~3,6 s. |
| `SELECT` de invariantes no PostgreSQL | **PASSOU** — após o burst: `count=125`, `max(numero)=125`, `proximo_numero=126`; 0 números duplicados, 0 senhas sem evento, 0 eventos órfãos e 0 filas desalinhadas. |
| `python scripts/concurrent_calls.py` | **PASSOU** — dois guichês do posto 1 chamaram senhas diferentes (números 2 e 3; guichês 3 e 1). |
| Verificação de chamadas concorrentes | **PASSOU** — 0 guichês com duas senhas CHAMADA, 0 senha associada a dois guichês, 0 senha CHAMADA sem evento `SENHA_CHAMADA` e 0 guichê de outro posto. |
| `python scripts/consistency_test.py` | **PASSOU** — mesma `Idempotency-Key` + mesmo payload em paralelo gerou **uma** senha, com `reutilizada` `[False, True]`; payload divergente gerou 201/409 e o reuso posterior retornou 409. |
| Invariantes de idempotência | **PASSOU** — 0 chaves duplicadas na mesma fila; 0 senhas sem evento `SENHA_EMITIDA`. |
| Falha induzida no `INSERT` de `eventos` | **PASSOU** — constraint temporária `CHECK (false) NOT VALID` fez a emissão retornar 503; contadores antes/durante/depois idênticos (senhas 131, eventos 135, `proximo_numero` 132); nenhuma senha ou evento parcial persistido. Constraint removida em `finally` e confirmada ausente. |
| Recuperação após remover a constraint | **PASSOU** — nova emissão retornou 201/200 e criou a senha 132 com o respectivo evento `SENHA_EMITIDA`. |
| Retentativa com a mesma chave que falhou | **PASSOU** — primeira tentativa com constraint retornou 503; após removê-la, a mesma `Idempotency-Key` retornou 201 com `reutilizada=false`; exatamente 1 senha e 1 evento para a chave, provando que o rollback não deixou registro de idempotência parcial. |
| `python scripts/smoke.py` com backlog | **PASSOU** — limite ajustado para `quantidade_aguardando+10`; executou 131 chamadas sequenciais com 130 senhas à frente, finalizou a própria senha e esvaziou a fila (`0 AGUARDANDO`). Duração ~292 s. |
| Medição de latência sequencial | **OBSERVADO** — ~2,1 s por requisição abrindo nova conexão TLS e ~0,42 s reutilizando `requests.Session`; o custo é do encaminhamento de porta/TLS local no Windows, não da transação no PostgreSQL. |
| Varredura final de invariantes | **PASSOU** — 0 duplicados, 0 filas desalinhadas, 0 senhas sem evento de emissão, 0 eventos de emissão duplicados, 0 chamadas duplicadas e 0 eventos órfãos. |

**Arquivos alterados na F2:** `scripts/consistency_test.py` (novo teste de idempotência concorrente), `scripts/smoke.py` (limite dinâmico conforme a fila), `docs/PROGRESSO.md` e `docs/ACEITE.md`. Nenhuma alteração em `api/`, `worker/`, `database/`, `compose.yaml` ou `openapi.yaml`.

**Observações metodológicas da F2:**

- O teste de rollback por `REVOKE INSERT` não funcionou porque `sac` é superusuário (`rolsuper=t`) e ignora privilégios. A abordagem foi trocada por uma constraint temporária que falha apenas no `INSERT` de `eventos`, sem alterar o restante da tabela.
- A tentativa com `REVOKE` ocorreu quando o Docker já estava parado; por isso não houve alteração de dados nem de privilégios.
- O Docker Desktop parou sozinho uma vez durante a F2. Após reiniciar, `docker compose up -d --scale api=2` restaurou os 6 serviços e os volumes; as 129 senhas anteriores foram preservadas.

### F3 — execução real

| Comando / verificação | Resultado |
|---|---|
| `python scripts/websocket_test.py` | **PASSOU** — cliente WS autenticado recebeu `FILA_ATUALIZADA` de `SENHA_EMITIDA` em ~7 s (exit 0). |
| `python scripts/ws_flow_test.py` | **PASSOU** — 2 conexões WS em réplicas distintas (`ad18369e1411` e `ae2270658db0`); `SENHA_EMITIDA`, `SENHA_CHAMADA` e `SENHA_FINALIZADA` chegaram nas duas. Os 3 eventos ficaram com `publicado_em`, tentativa registrada e linha em `eventos_processados`; cada evento gerou `websocket_forwarded` nas **duas** APIs. A republicação do mesmo evento gerou `duplicate_ignored`, sem novo fanout e sem nova entrega WS (24,0 s). |
| Outbox após o fluxo WS | **PASSOU** — 3 eventos do ticket com `publicado_em IS NOT NULL`, `tentativas >= 1` e registro de processamento; nenhum evento pendente. |
| `python scripts/dlq.py` | **PASSOU** — mensagem malformada sofreu retry 1 e 2 (`event_retry_scheduled`) e `event_dead_letter` na 3ª tentativa; `sac.events.dlq` foi de 0 para 1 (14,4 s). |
| `python scripts/broker_chaos.py` | **PASSOU** — com o RabbitMQ parado, a emissão retornou e a senha ficou `AGUARDANDO` com o evento no outbox (`publicado_em IS NULL`); após reiniciar o broker, o evento foi publicado e processado. Um novo ticket comprovou o WS recuperado, e as duas senhas permaneceram `AGUARDANDO` (40,4 s). |
| `python scripts/ws_reconnect_test.py` | **PASSOU** — a réplica que atendia o WS (`ae2270658db0`) foi parada; a conexão encerrou, o cliente reconectou em `ad18369e1411`, recebeu um novo evento e a consulta REST retornou `AGUARDANDO`. A réplica foi restaurada `healthy` e as 6 unidades do Compose voltaram (30,4 s). |
| `python scripts/cli_idle_test.py` | **PASSOU** — o CLI `acompanhar` recebeu um evento, ficou 15 s ocioso sem imprimir "Conexão indisponível" e sem reconectar, e recebeu um segundo evento na mesma conexão (23,2 s). |
| `python scripts/tracing.py` | **PASSOU** — o mesmo `correlation_id` apareceu em `event_persisted` (API), `event_processed`/`event_published` (Worker) e `websocket_forwarded` nas duas APIs. |
| Varredura final de invariantes | **PASSOU** — 288 eventos, 0 pendentes, 0 sem registro em `eventos_processados`, 0 órfãos e 0 duplicados; `sac.events.processing` e `sac.events.retry` vazias; DLQ com a única mensagem injetada. |

**Arquivos alterados na F3:** `scripts/ws_flow_test.py`, `scripts/broker_chaos.py`, `scripts/ws_reconnect_test.py` e `scripts/cli_idle_test.py` (novos testes), `scripts/dlq.py` (contagem via `rabbitmqctl` interno), `scripts/tracing.py` (aceita `duplicate_ignored`), `worker/src/republish_event.js` (helper de teste de duplicidade), `cliente-python/main.py` (timeout ocioso do WS), `docs/PROGRESSO.md` e `docs/ACEITE.md`. Nenhuma alteração em `api/src/`, `worker/src/worker.js`, `database/`, `compose.yaml` ou `openapi.yaml`.

**Observações metodológicas da F3:**

- A porta 15672 do RabbitMQ está mapeada no container, mas o encaminhamento do Docker Desktop para o host não responde (`docker inspect` mostra `HostPort 15672`, porém a conexão é recusada). Por isso a contagem da DLQ usa `rabbitmqctl` dentro do container e a republicação de duplicata usa um helper Node no worker.
- `worker/src/republish_event.js` foi criado depois do build da imagem; no container em execução é necessário `docker compose cp worker/src/republish_event.js worker:/app/worker/src/republish_event.js` (um rebuild também resolve).
- A notificação do primeiro evento publicado logo após a volta do broker pode se perder se o subscriber da API ainda não reconectou; o teste valida a persistência desse evento e comprova a volta do WS com um segundo ticket.
- `ws_reconnect_test.py` exigia 5 serviços `healthy`, mas apenas API (2), PostgreSQL e RabbitMQ declaram healthcheck no `compose.yaml`; a asserção foi corrigida para 4.

### F4 — execução real

| Comando / verificação | Resultado |
|---|---|
| `python scripts/balancing.py` | **PASSOU** — a API resolve `postgres` e `rabbitmq` por nome Docker (`172.18.0.5`/`172.18.0.4`); 20 requisições a `/health/ready` foram **10/10** para cada réplica, 0 erros, e as duas instâncias aparecem nos logs JSON (42,9 s). |
| `python scripts/chaos.py` | **PASSOU** — réplica `ae2270658db0` parada; o gateway atendeu em `ad18369e1411`; a senha 144 foi emitida e consultada via REST **durante a queda**; a réplica voltou `healthy` e os dois nós voltaram a atender (35,1 s). |
| `python scripts/security_test.py` | **PASSOU** — 12 verificações: 403 para ticket alheio, guichê de outro posto e guichê de cidadão; 401 sem token; JWT adulterado, assinado com outro segredo, expirado, `alg=none` e com audiência/emissor divergentes → 401; token válido de ATENDENTE do posto 2 em guichê do posto 1 → 403 (escopo checado, não só assinatura); WSS com token válido → `CONECTADO` e token inválido → 401; TLSv1.3 negociado; certificado local recusado por CA pública; Compose sem publicação da porta 80 e API não responde em HTTP puro (41,8 s). |
| `python scripts/circuit_breaker_test.py` | **PASSOU** — com o RabbitMQ parado, o worker abriu o circuito após **3 falhas** (`circuit_opened`) e registrou `outbox_relay_retry` com `breaker=OPEN`; após reiniciar, passou por `circuit_half_open` e `circuit_closed`; a senha 149 foi publicada e processada (27,7 s). |
| `docker compose --profile observabilidade up -d logs` + `python scripts/telemetry_test.py` | **PASSOU** — Dozzle v8.14.12 responde em `http://127.0.0.1:8081` e o stream `/api/events/stream` lista os 6 serviços do projeto (`api-1`, `api-2`, `worker`, `postgres`, `rabbitmq`, `traefik`). |
| `python scripts/tracing.py` | **PASSOU** — o mesmo `correlation_id` apareceu em `event_persisted` (API), `event_published`/`event_processed` (Worker) e `websocket_forwarded` nas duas APIs (10,9 s). |
| `python scripts/secrets_check.py` | **PASSOU** — 4 segredos locais e padrões AWS/JWT ausentes em 60 arquivos do projeto e em 5.904 linhas de log dos containers; `.gitignore` cobre `.env`, `.venv/` e `node_modules/`; nenhum `.tfvars` local. |
| Varredura final de invariantes | **PASSOU** — 295 eventos, 0 pendentes, 0 sem registro processado, 0 órfãos e 0 duplicados; `sac.events.processing`/`retry` vazias; DLQ com a única mensagem injetada. |

**Arquivos alterados na F4:** `scripts/balancing.py`, `scripts/chaos.py` (ampliado), `scripts/security_test.py` (ampliado), `scripts/circuit_breaker_test.py`, `scripts/telemetry_test.py` e `scripts/secrets_check.py` (novos), `docs/PROGRESSO.md` e `docs/ACEITE.md`. Nenhuma alteração em `api/`, `worker/src/`, `database/`, `compose.yaml` ou `openapi.yaml`.

**Observações metodológicas da F4:**

- A porta 80 do host é atendida por um nginx do WSL (`wslrelay`), não pelo projeto. Por isso o teste verifica o mapeamento publicado pelo Compose e que a API não responde em HTTP puro, em vez de exigir porta 80 fechada.
- O Docker Desktop caiu antes da primeira execução do circuit breaker; a stack foi restaurada com `docker compose up -d --scale api=2` e os dados preservados (151 senhas e 293 eventos no momento).
- O Dozzle está no profile `observabilidade` e não sobe por padrão; é preciso iniciá-lo explicitamente. A porta 8081 funciona no host (diferente da 15672 do RabbitMQ).
- O certificado TLS local é autoassinado pelo Traefik. TLSv1.3 e WSS funcionam, mas o certificado não é confiável por CA pública; isso é esperado no ambiente de demonstração e não representa PKI de produção.

## 3. Estado por requisito

Estados usados: **EXISTE**, **FUNCIONA TESTADO**, **QUEBRADO**, **NÃO TESTADO**, **FALTA**. Auditoria de código não equivale a teste executado.

| Requisito | Estado | Evidência / observação |
|---|---|---|
| RF01 listar postos | FUNCIONA TESTADO | CLI `postos` retornou 2 postos via Traefik/API. |
| RF02 fila/ETA | FUNCIONA TESTADO | CLI `fila --posto 1` retornou `posto`, `tempo_espera_minutos`, contagem e guichês. |
| RF03 emitir senha | FUNCIONA TESTADO | Smoke e `consistency_test.py`: mesma chave/payload gera uma senha; payload divergente retorna 409. |
| RF04 consultar senha | FUNCIONA TESTADO | Smoke consultou a própria senha; `security_test` comprovou 403 para ticket alheio. |
| RF05 chamar próxima | FUNCIONA TESTADO | Smoke chamou uma senha; `concurrent_calls.py` provou duas chamadas simultâneas com senhas diferentes. |
| RF06 finalizar | FUNCIONA TESTADO | Smoke finalizou a senha chamada (CHAMADA → FINALIZADA). |
| RF07 notificar por eventos | FUNCIONA TESTADO | `ws_flow_test.py` entregou emissão, chamada e finalização via WS em duas conexões e duas réplicas; fanout confirmado nas duas APIs. |
| RF08 histórico/outbox | FUNCIONA TESTADO (observado) | Logs reais mostram `event_persisted` na API e `event_published`/`event_processed` no Worker; outbox com 0 pendentes ao final da F3. |
| RF09 integração Python/Node | FUNCIONA TESTADO | CLI Python consumiu API Node via HTTPS/Traefik. |
| RNF01 processos autônomos | PARCIAL | `docker compose ps` mostrou 6 serviços e 2 APIs saudáveis; tráfego entre nós não instrumentado. |
| RNF02 consistência/concorrência | FUNCIONA TESTADO | Burst de 60 sem duplicados, lock de fila, idempotência concorrente e rollback induzido comprovados. |
| RNF03 eventos resilientes | FUNCIONA TESTADO | Outbox sem pendentes; retry limitado com DLQ; broker parado preservou senha/evento e recuperou publicação e processamento; entrega duplicada ignorada. |
| RNF04 escala/roteamento | PARCIAL | 2 APIs e Traefik ativos; WS provou clientes em réplicas distintas, mas balanceamento de carga não foi medido. |
| RNF05 segurança | PARCIAL | 401/403, JWT adulterado/expirado/`alg=none` e escopo de posto comprovados; WSS/TLSv1.3 ativos com certificado de desenvolvimento; AWS Secrets Manager pendente. |
| RNF06 observabilidade | FUNCIONA TESTADO | `tracing.py` correlaciona API → Worker → fanout; Dozzle lista os 6 serviços e exibe os logs agregados. |
| RNF07 reprodutibilidade | PARCIAL | Compose build/up/config passaram; **FALTA** `.git`, `package-lock.json`; CI não executado. |
| RNF08 falhas controladas | FUNCIONA TESTADO | Circuit breaker do worker ensaiado (OPEN → HALF_OPEN → CLOSED) com broker parado; caos de API, broker e WS executados. |
| C1 comunicação | FUNCIONA TESTADO | REST/OpenAPI/CLI e WS reais; eventos entregues a duas conexões em réplicas distintas. |
| C2 concorrência/escala | PARCIAL | Concorrência comprovada (A05/A06); 2 réplicas ativas, mas balanceamento/throughput entre nós ficam para F4. |
| C3 resiliência | FUNCIONA TESTADO | Rollback, atomicidade, broker parado, retry/DLQ, reconexão WS e circuit breaker (OPEN → HALF_OPEN → CLOSED) comprovados. |
| C4 nomes/roteamento | FUNCIONA TESTADO | DNS Docker por nome, balanceamento 10/10 entre réplicas, entrada/saída de nó com nova emissão durante a queda. |
| C5 segurança | PARCIAL | JWT/RBAC/TLS/WSS reais e testados; certificado de desenvolvimento sem CA pública; AWS Secrets Manager não executado. |
| C6 logs | FUNCIONA TESTADO | Correlation ID comprovado em API, Worker e fanout por `tracing.py`; logs agregados no Dozzle. |
| C7 DevOps | PARCIAL | Build/up/config passaram; sem Git, lockfile ou CI remota. |
| C8 demonstração | PARCIAL | Roteiros de carga, caos, DLQ, broker, reconexão, circuit breaker e tracing ensaiados; ensaio completo da demo pendente (A18). |

**A02, A03, A04, A05, A06, A07, A08, A09, A10, A11, A12, A13, A15 e A17 passaram com evidência real (F1–F4).** Permanecem não validados: A01 (clone limpo), A14 (AWS), A16 (CI/Git) e A18 (explicação dos integrantes).

## 4. Defeitos e riscos

### RESOLVIDOS NA F1/F2

1. `scripts/security_test.py` usava o guichê 3 como se fosse de outro posto; o seed o coloca no posto 1. Corrigido para o guichê 2 e **executado com PASS**.
2. `scripts/concurrent_calls.py` usava os guichês `(1, 2)`; o guichê 2 é do posto 2. Corrigido para `(1, 3)` e **executado na F2 com PASS** (senhas 2 e 3 em guichês distintos).
3. `openapi.yaml` não documentava 400/401/403/404/409 em várias rotas e não tinha schema para a resposta de `chamar`. Foram adicionados responses reutilizáveis, o schema `Chamada` e os códigos reais; o arquivo passou no `openapi-spec-validator`.
4. A F2 criou `scripts/consistency_test.py`, que cobre idempotência concorrente e reuso com payload divergente; **executado com PASS**.
5. A atomicidade senha + evento foi provada com uma constraint temporária `CHECK (false) NOT VALID` em `eventos`: a emissão retornou 503 e nenhuma senha, evento ou incremento de fila permaneceu. A constraint foi removida e a recuperação foi validada.
6. `REVOKE INSERT ON eventos` **não** serve para induzir falha porque o usuário `sac` é superusuário (`rolsuper=t`). O teste foi refeito com constraint; a tentativa com `REVOKE` não alterou dados porque o Docker estava parado.
7. `scripts/smoke.py` usava limite fixo de 100 chamadas; com o backlog de 130 senhas gerado pela F2, isso produzia falso negativo. O limite agora é `quantidade_aguardando+10` e o smoke passou com 131 chamadas.

### RESOLVIDOS NA F3

1. O timeout ocioso do cliente Python foi corrigido: `timeout=8` continua valendo para o handshake e, depois, `ws.settimeout(60)` com `WebSocketTimeoutException` tratado como ociosidade. `cli_idle_test.py` comprovou 15 s sem reconexão e entrega posterior na mesma conexão.
2. `scripts/tracing.py` agora aceita `duplicate_ignored` como processamento válido do worker, eliminando o falso negativo apontado na F2.
3. `scripts/dlq.py` passou a contar a DLQ com `rabbitmqctl` dentro do container, porque a porta 15672 não é alcançável no host apesar do mapeamento.
4. `scripts/ws_reconnect_test.py` validava 5 serviços `healthy`, mas só 4 declaram healthcheck; a asserção foi corrigida e o teste passou.
5. A entrega duplicada foi tratada como caminho normal: `republish_event.js` republica um evento persistido, o worker registra `duplicate_ignored`, `eventos_processados` não ganha linha nova e não há novo fanout.

### RESOLVIDOS NA F4

1. `scripts/balancing.py` comprovou DNS Docker por nome e distribuição 10/10 entre as duas réplicas, com ambas as instâncias nos logs JSON.
2. `scripts/chaos.py` foi ampliado: além do failover, agora emite e consulta uma senha **durante** a queda e confirma a volta dos dois nós depois de restaurar a réplica.
3. `scripts/security_test.py` foi ampliado para 12 verificações: JWT adulterado/expirado/`alg=none`/audiência-errada, escopo de posto com token válido, WSS aceito/recusado, TLSv1.3 e ausência de HTTP puro.
4. A suposição de que a porta 80 deveria estar fechada estava errada: ela é atendida por um nginx do WSL. O teste agora verifica o mapeamento do Compose e que a API não responde em HTTP puro.
5. O circuit breaker do worker, antes apenas existente, foi ensaiado: abriu após 3 falhas, passou por HALF_OPEN e fechou após a recuperação.
6. Dozzle foi iniciado pelo profile `observabilidade` e `scripts/telemetry_test.py` comprovou a visão agregada dos 6 serviços.
7. `scripts/secrets_check.py` comprovou que os 4 segredos locais e padrões AWS/JWT não aparecem em arquivos nem em 5.904 linhas de log.

### PENDENTES

1. A01 (clone limpo) não pode ser executado: não há repositório Git, então não existe clone para validar.
2. A14 (AWS Secrets Manager/`GetSecretValue`) continua bloqueado por ausência de credenciais e autorização de custo; não foi executado.
3. A16 (CI verde) continua bloqueado: sem `.git`, sem `package-lock.json` e sem execução de pipeline remoto.
4. A18 depende dos integrantes explicarem o fluxo; não é automatizável.
5. `scripts/testing.py:8` não normaliza barra final em `SAC_URL`; uma variável com `/` pode gerar `//api/...`. Normalização simples.
6. Latência sequencial medida em ~2,1 s por requisição com nova conexão TLS e ~0,42 s com `requests.Session`; para a F6, reutilizar sessão ou esvaziar a fila antes da demonstração.
7. A porta 15672 do RabbitMQ não é encaminhada ao host pelo Docker Desktop; o caminho interno (`rabbitmqctl`/helper no worker) funciona. Se a demonstração exigir o Management UI, recriar o container ou revisar o mapeamento.
8. `worker/src/republish_event.js` é um helper de teste posterior ao build; containers novos só o terão após rebuild, e o container atual exigiu `docker compose cp`.
9. O Docker Desktop parou sozinho mais de uma vez durante a F2/F3/F4; a recuperação foi `docker compose up -d --scale api=2`, com dados preservados.
10. O Dozzle está no profile `observabilidade` e precisa ser iniciado explicitamente antes da demo.
11. O certificado TLS local é autoassinado e não é confiável por CA pública; isso é esperado no ambiente de demonstração, mas impede declarar PKI de produção.

## 5. Divergências documentais

- Não foi encontrada contradição de escopo entre `PRD.md`, `MVP.md` e `ARQUITETURA_ALVO.md`; as rotas e os componentes conferem.
- `docs/VALIDACAO_LOCAL.md` descreve um ambiente sem Docker; nesta sessão o Compose foi efetivamente construído e iniciado. O documento histórico não deve ser usado como estado atual sem atualização.
- Os scripts assumem IDs fixos de postos/guichês derivados do seed. O seed não declara IDs explícitos, mas a consulta ao banco confirmou: guichês 1/3 no posto 1 e 2/4 no posto 2. O `concurrent_calls.py` foi executado na F2 com PASS.
- A divergência acadêmica entre fator 0,3 e 0,4 do barema continua pendente de confirmação docente; não afeta o código.

## 6. Próximo passo

**F4 concluída.** Aguardando autorização para iniciar a **F5 — Automação e serviço de segredos (C5/C7)**:

1. Garantir `.env.example`, `scripts/setup_env.py`, Compose e CI realmente executando.
2. Gerar `package-lock.json` e versioná-lo; avaliar `npm ci` no CI/contêiner se compatível.
3. Inicializar Git e validar um clone limpo (A01) sem versionar `.env`, `.venv`, `node_modules` ou evidências locais.
4. AWS somente com autorização explícita: `terraform fmt/validate/plan` e leitura real do segredo com permissão mínima; não executar `apply` sem custo aprovado.
5. Atualizar `docs/PROGRESSO.md` e `docs/ACEITE.md` somente com o que passar de fato.

**Não iniciar F6 (ensaio final da demo) sem autorização.**
