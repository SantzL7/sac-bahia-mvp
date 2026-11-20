# Progresso factual do MVP

**Última atualização:** 2026-11-18 | **Situação:** F1–F6 concluídas. O ensaio final da demo passou de ponta a ponta: `smoke`, concorrência, burst, WebSocket, tracing, caos de API, DLQ, segurança e circuit breaker, sem falhas. Permanecem não validados apenas A14 (AWS sem credencial válida), A16 (CI sem runner remoto) e A18 (explicação dos integrantes). Versão final marcada com tag Git.

## 0. Estado atual do ambiente

- Docker Desktop iniciado; `docker info` responde.
- `.env` local criado por `py scripts/setup_env.py --quiet` (conteúdo não versionado).
- `.venv` criado com `requests`, `websocket-client` e validador OpenAPI.
- Stack em execução: PostgreSQL, RabbitMQ, Traefik, Worker e **2 réplicas da API**.
- Volumes criados; nenhum `docker compose down -v` foi executado.
- Dados de demonstração foram gerados pelos smokes; o banco não é um ambiente limpo.
- Durante a F2 e a F3 o Docker Desktop parou sozinho mais de uma vez; foi reiniciado e a stack voltou com `docker compose up -d --scale api=2`. Volumes e dados foram preservados.
- Estado após a F6: 391 eventos, 0 pendentes no outbox e 391 com registro em `eventos_processados`; 226 senhas (67 AGUARDANDO, 153 CHAMADA, 6 FINALIZADA). `sac.events.dlq` contém 2 mensagens malformadas injetadas pelos ensaios de DLQ. Nenhuma constraint temporária permanece.
- Dozzle iniciado com `docker compose --profile observabilidade up -d logs` e exposto em `127.0.0.1:8081`; a stack tem 7 containers (o profile não sobe por padrão).
- O clone de validação da F5 foi executado em `C:\Users\Santz\AppData\Local\Temp\opencode\sac_bahia_clone_f5`, com projeto, rede e portas próprios, e depois desmontado com `docker compose down` (sem `-v`). A demo principal não foi afetada.
- Ensaio final da F6 executado na demo principal, com as 2 réplicas, Dozzle ativo e dados preservados.


## 1. Inventário real (não presumido)

- 61 arquivos rastreados no Git (commit `aae029d`), excluindo `node_modules` e `__pycache__`.
- Componentes presentes: `api/` (Node/Express + WS), `worker/` (outbox + consumidor), `cliente-python/`, `database/` (schema/seed), `shared/`, `scripts/`, `tests/`, `infra/terraform/`, `.github/workflows/`.
- Contratos/configuração presentes: `openapi.yaml`, `compose.yaml`, `compose.aws.yaml`, `Dockerfile`, `package.json`, `package-lock.json`, `.env.example`, `.gitignore`, `.dockerignore`.
- Documentação presente: PRD, MVP, REQUISITOS, ARQUITETURA, ARQUITETURA_ALVO, MATRIZ_BAREMA, PLANO_EXECUCAO, ACEITE, ENTREGA, VALIDACAO_LOCAL, PROMPTS_OPENCODE, GUIA_OPENCODE.
- Artefatos locais não versionados: `.env`, `.venv`, `node_modules` (todos cobertos pelo `.gitignore`).
- Artefatos ainda ausentes: `docs/evidencias/`, infraestrutura AWS real e pipeline remoto.
- `package-lock.json` (87 KB) foi gerado na F5 e é versionado; `npm ci` instala 178 pacotes a partir dele.

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
| Smokes REST/WS/RabbitMQ/PostgreSQL, burst, chaos, DLQ, tracing | **F0 NÃO EXECUTADOS**; **F1:** `smoke.py` e `security_test.py` com PASS; **F2:** `burst.py`, `concurrent_calls.py` e `consistency_test.py` com PASS; **F3:** `websocket_test.py`, `ws_flow_test.py`, `dlq.py`, `broker_chaos.py`, `ws_reconnect_test.py`, `cli_idle_test.py` e `tracing.py` com PASS; **F4:** `balancing.py`, `chaos.py` (ampliado), `security_test.py` (ampliado), `circuit_breaker_test.py`, `telemetry_test.py`, `secrets_check.py` e `tracing.py` com PASS; **F5:** `smoke.py` e `balancing.py` com PASS no clone limpo. |
| AWS Secrets Manager (`terraform plan/apply`, `GetSecretValue`) | **FALHOU / BLOQUEADO** — `aws sts get-caller-identity` e `scripts/check-aws-secret.js` retornaram `InvalidClientTokenId` (credenciais inválidas/expiradas); Terraform não está instalado. Nenhum recurso ou custo foi criado. |

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

### F5 — execução real

| Comando / verificação | Resultado |
|---|---|
| `npm install --package-lock-only --no-audit --no-fund` | **PASSOU** — `package-lock.json` gerado com 87.290 bytes, sem alterar `node_modules`. |
| `npm ci --no-audit --no-fund` | **PASSOU** — 178 pacotes instalados a partir do lockfile em 4 s, exit 0. |
| `npm run test:all` | **PASSOU** — análise sintática + 4/4 testes unitários. |
| `python -m openapi_spec_validator openapi.yaml` | **PASSOU** — `openapi.yaml: OK`. |
| `git init -b main` + commit | **PASSOU** — commit `aae029d`, **61 arquivos rastreados**, árvore limpa; `.env`, `.venv/`, `node_modules/` e `__pycache__/` ignorados (confirmado por `git check-ignore` e `git ls-files`). |
| Clone limpo + `py scripts/setup_env.py --quiet` | **PASSOU** — clone em diretório temporário com `.env` novo; `git status` limpo; `docker compose config -q` exit 0. |
| Clone + `docker compose up -d --build --scale api=2` | **PASSOU** — 6 serviços `Up`; API-1, API-2, PostgreSQL e RabbitMQ `healthy`. |
| Clone + `python scripts/smoke.py` | **PASSOU** — REST, idempotência, RBAC, consulta, chamada e finalização (27,3 s), exit 0. |
| Clone + `python scripts/balancing.py` | **PASSOU** — DNS Docker por nome; 20 requisições **10/10** em cada réplica (`b7cc5dbd4f7b`/`80562ba1023a`), 0 erros (42,4 s), exit 0. |
| `aws sts get-caller-identity` / `node scripts/check-aws-secret.js` | **FALHOU** — `InvalidClientTokenId`: as credenciais AWS presentes estão inválidas ou expiradas. Nenhum recurso foi criado e nenhum custo foi incorrido. |
| `terraform version` | **PASSOU em 2026-11-20** — Terraform 1.17.1 instalado via `winget`. O `main.tf` tinha bloco `variable` de uma linha (HCL inválido) e foi corrigido; `terraform fmt -check`, `init -backend=false` (provider AWS 5.100.0) e `validate` passaram. `plan/apply` ainda dependem de credencial AWS válida. |
| `py -m compileall -q cliente-python scripts`, `docker compose config -q`, parsing do CI | **PASSOU** — exit 0; workflow YAML válido (`CI_YAML_OK`). |
| Estado final da demo após o clone | **PASSOU** — `/health/ready` 200 em `ad18369e1411`; 156 senhas (19 AGUARDANDO, 132 CHAMADA, 5 FINALIZADA), 298 eventos, 0 pendentes, 298 processados. |

**Arquivos alterados na F5:** `package-lock.json` (novo), `.github/workflows/ci.yml` (`npm ci` + validação OpenAPI), `scripts/balancing.py` (DNS deriva o container de `docker compose ps -q api`), `docs/PROGRESSO.md` e `docs/ACEITE.md`. Nenhuma alteração em `api/`, `worker/src/`, `database/`, `openapi.yaml` ou `compose.yaml`.

**Observações metodológicas da F5:**

- O CI foi atualizado para `npm ci` e para validar o `openapi.yaml`, mas **não existe repositório remoto nem runner**: o workflow foi validado por parsing YAML e os passos foram executados manualmente no host. A16 continua NÃO VALIDADO.
- O primeiro clone compartilhava a rede fixa `sac-bahia_public` e o router Traefik `sac` com a demo, causando descoberta cruzada das APIs (401 por segredo JWT diferente e 201 onde se esperava 409). O clone de teste foi isolado com projeto, rede, router e portas próprios; essa limitação de dois projetos no mesmo host está registrada em PENDENTES.
- O Docker Desktop caiu durante o primeiro teste do clone, derrubando a réplica `api-2` e produzindo 401 transitório. Após reiniciar e restaurar `--scale api=2`, o mesmo token foi validado localmente (assinatura HS256 correta) e o fluxo passou.
- O `secrets_check.py` da F4 continua válido: o lockfile novo não contém segredos locais nem padrões AWS/JWT.

### F6 — ensaio final da demo (execução real)

Ensaio executado em 2026-11-18 na demo principal, com 2 réplicas da API, PostgreSQL, RabbitMQ, Worker, Traefik e Dozzle ativos.

| Ordem | Comando | Resultado |
|---|---|---|
| 1 | `python scripts/smoke.py` | **PASSOU** — REST/contrato, idempotência, RBAC, consulta, chamada e finalização com backlog de 19 senhas; fila drenada e uma senha finalizada (58,3 s). |
| 2 | `python scripts/concurrent_calls.py` | **PASSOU** — guichês 1 e 3 chamaram senhas diferentes (155 e 156), sem conflito (8,6 s). |
| 3 | `python scripts/burst.py` | **PASSOU** — 60 emissões simultâneas, 60 IDs e números únicos (2,9 s). |
| 4 | `python scripts/websocket_test.py` | **PASSOU** — `FILA_ATUALIZADA`/`SENHA_EMITIDA` entregue por WSS em 7,0 s. |
| 5 | `python scripts/tracing.py` | **PASSOU** — mesmo `correlation_id` em `http_request`, `event_persisted`, `event_published`/`event_processed` e `websocket_forwarded` nas duas APIs (10,6 s). |
| 6 | `python scripts/chaos.py` | **PASSOU** — réplica `ae2270658db0` parada; gateway atendeu em `ad18369e1411`; senha 220 emitida e consultada durante a queda; réplica restaurada e os dois nós voltaram a atender (31,7 s). |
| 7 | `python scripts/dlq.py` | **PASSOU** — DLQ aumentou de 1 para 2 após retries da mensagem malformada (13,7 s). |
| 8 | `python scripts/security_test.py` | **PASSOU** — 12 verificações de JWT/RBAC/escopo/WSS/TLS/HTTP puro (40,5 s). |
| 9 | `python scripts/circuit_breaker_test.py` | **PASSOU** — broker parado: `circuit_opened` (3 falhas) e `breaker=OPEN`; recuperação: `HALF_OPEN` → `CLOSED`; senha 223 publicada e processada (28,2 s). |
| 10 | `python scripts/secrets_check.py` | **PASSOU** — 4 segredos e padrões AWS/JWT ausentes em 61 arquivos e 8.290 linhas de log (4,3 s). |
| 11 | Varredura final de invariantes | **PASSOU** — 391 eventos, 0 pendentes, 0 sem processamento, 0 órfãos, 0 duplicados; 226 senhas (67 AGUARDANDO, 153 CHAMADA, 6 FINALIZADA); `processing`/`retry` vazias; DLQ com 2 injetadas. |

**Totais do ensaio:** 11 verificações, todas com exit 0, ~3,6 min de execução somada.

**Preparação offline:** todas as imagens usadas estão locais (`sac-bahia-api`, `sac-bahia-worker`, `postgres:16-alpine`, `rabbitmq:3.13-management-alpine`, `traefik:v3.6.16`, `amir20/dozzle:v8`); os scripts apontam para `https://localhost:8443` e `http://127.0.0.1:8081`, sem dependência de internet. O build não é necessário na sala se as imagens estiverem carregadas.

**Arquivos alterados na F6:** `docs/PROGRESSO.md`, `docs/ACEITE.md` e `docs/ENTREGA.md` (checklist de ensaio). Nenhuma alteração em `api/`, `worker/src/`, `database/`, `openapi.yaml`, `compose.yaml` ou scripts de teste.

**Observações do ensaio:**

- Nenhuma queda do Docker Desktop ocorreu nesta fase; a stack permaneceu saudável do início ao fim.
- O `smoke.py` consumiu o backlog existente, por isso o total de AGUARDANDO caiu e o de CHAMADA subiu; isso é esperado e não é falha.
- O ensaio cobriu também os blocos de segurança e circuit breaker do roteiro, além dos 7 scripts exigidos na F6.
- A18 continua **NÃO VALIDADO**: o roteiro está preparado, mas a explicação individual dos integrantes não é automatizável.

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
| RNF04 escala/roteamento | PARCIAL | 2 APIs e Traefik ativos; balanceamento 10/10 entre réplicas comprovado na F4; throughput/latência sob carga entre nós ainda não medidos. |
| RNF05 segurança | PARCIAL | 401/403, JWT adulterado/expirado/`alg=none` e escopo de posto comprovados; WSS/TLSv1.3 ativos com certificado de desenvolvimento; AWS Secrets Manager pendente. |
| RNF06 observabilidade | FUNCIONA TESTADO | `tracing.py` correlaciona API → Worker → fanout; Dozzle lista os 6 serviços e exibe os logs agregados. |
| RNF07 reprodutibilidade | FUNCIONA TESTADO | `package-lock.json` versionado, `npm ci` (178 pacotes), Git com commit `aae029d` (61 arquivos) e clone limpo com `--scale api=2`, smoke e balanceamento 10/10. CI remota ainda não executada. |
| RNF08 falhas controladas | FUNCIONA TESTADO | Circuit breaker do worker ensaiado (OPEN → HALF_OPEN → CLOSED) com broker parado; caos de API, broker e WS executados. |
| C1 comunicação | FUNCIONA TESTADO | REST/OpenAPI/CLI e WS reais; eventos entregues a duas conexões em réplicas distintas. |
| C2 concorrência/escala | FUNCIONA TESTADO | Burst e chamadas concorrentes sem duplicados; 2 réplicas reais com balanceamento 10/10 comprovado na F4. |
| C3 resiliência | FUNCIONA TESTADO | Rollback, atomicidade, broker parado, retry/DLQ, reconexão WS e circuit breaker (OPEN → HALF_OPEN → CLOSED) comprovados. |
| C4 nomes/roteamento | FUNCIONA TESTADO | DNS Docker por nome, balanceamento 10/10 entre réplicas, entrada/saída de nó com nova emissão durante a queda. |
| C5 segurança | PARCIAL | JWT/RBAC/TLS/WSS reais e testados; certificado de desenvolvimento sem CA pública; AWS Secrets Manager não executado. |
| C6 logs | FUNCIONA TESTADO | Correlation ID comprovado em API, Worker e fanout por `tracing.py`; logs agregados no Dozzle. |
| C7 DevOps | PARCIAL | Git, lockfile, `npm ci`, clone limpo e build/up/config passaram; falta execução de pipeline remoto (A16) e AWS real (A14). |
| C8 demonstração | PARCIAL | Ensaio completo da F6 passou: 11 verificações com exit 0, cobrindo REST, concorrência, burst, WS, tracing, caos, DLQ, segurança e circuit breaker. A18 (explicação individual dos integrantes) segue pendente. |

**A01, A02, A03, A04, A05, A06, A07, A08, A09, A10, A11, A12, A13, A15 e A17 passaram com evidência real (F1–F5).** Permanecem não validados: A14 (AWS Secrets Manager), A16 (CI remota) e A18 (explicação dos integrantes).

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

### RESOLVIDOS NA F5

1. `package-lock.json` foi gerado e versionado; `npm ci` instalou 178 pacotes em 4 s e `npm run test:all` passou 4/4.
2. O CI passou a usar `npm ci` e a validar `openapi.yaml`; o YAML foi parseado com sucesso e os passos foram executados manualmente.
3. Git foi inicializado em `main`, com `.env`, `.venv/`, `node_modules/` e `__pycache__/` ignorados; commit `aae029d` com 61 arquivos e árvore limpa.
4. O fluxo de clone limpo foi comprovado (A01): `.env` novo, `docker compose config -q`, build/up com 2 réplicas, smoke 27,3 s e balanceamento 10/10.
5. `scripts/balancing.py` deixou de depender do nome fixo `sac-bahia-api-1`: deriva o container de `docker compose ps -q api`, funcionando em qualquer projeto Compose.
6. Foi identificado e contornado o acoplamento entre projetos Compose no mesmo host: rede fixa `sac-bahia_public` e router `sac` fazem um Traefik descobrir as APIs do outro. O clone de teste usou rede/router/portas próprios.

### RESOLVIDOS NA F6

1. O ensaio final foi executado na ordem do roteiro, sem falhas: `smoke`, `concurrent_calls`, `burst`, `websocket_test`, `tracing`, `chaos`, `dlq`, `security_test` e `circuit_breaker_test`, todos com exit 0.
2. Invariantes finais confirmados: 391 eventos, 0 pendentes/órfãos/duplicados; filas `processing`/`retry` vazias; DLQ com as 2 mensagens injetadas.
3. Cenário offline verificado: imagens locais e endpoints `localhost`, sem dependência de internet para a demo.
4. Checklist de entrega (`docs/ENTREGA.md`) revisado com evidência do ensaio.

### PENDENTES

1. A14 (AWS Secrets Manager/`GetSecretValue`) está bloqueado: as credenciais disponíveis retornam `InvalidClientTokenId`. Terraform 1.17.1 já está instalado e `fmt/init/validate` passaram em `sa-east-1`; falta credencial válida para `plan/apply`, gravação do valor do segredo e leitura real. Não houve custo nem criação de recurso.
2. A16 (CI remota) continua bloqueado: não há repositório remoto nem runner; o workflow foi validado apenas localmente (YAML + passos manuais). O `gh` 2.105.0 está instalado, mas não autenticado.
3. A18 depende dos integrantes explicarem o fluxo; não é automatizável.
4. Dois projetos Compose no mesmo host compartilham a rede fixa `sac-bahia_public` e o router Traefik `sac`; isso permite descoberta cruzada das APIs (401 por JWT diferente, 201 onde se esperava 409). Para o clone foi usado isolamento total; a demo principal mantém o nome fixo.
5. `scripts/testing.py:8` não normaliza barra final em `SAC_URL`; uma variável com `/` pode gerar `//api/...`. Normalização simples.
6. Latência sequencial medida em ~2,1 s por requisição com nova conexão TLS e ~0,42 s com `requests.Session`; para a F6, reutilizar sessão ou esvaziar a fila antes da demonstração.
7. A porta 15672 do RabbitMQ não é encaminhada ao host pelo Docker Desktop; o caminho interno (`rabbitmqctl`/helper no worker) funciona. Se a demonstração exigir o Management UI, recriar o container ou revisar o mapeamento.
8. `worker/src/republish_event.js` é um helper de teste posterior ao build; containers novos só o terão após rebuild, e o container atual exigiu `docker compose cp`.
9. O Docker Desktop parou sozinho mais de uma vez durante a F2/F3/F4/F5; a recuperação foi `docker compose up -d --scale api=2`, com dados preservados. Durante o clone, a queda derrubou uma réplica e gerou 401 transitório até a restauração.
10. O Dozzle está no profile `observabilidade` e precisa ser iniciado explicitamente antes da demo.
11. O certificado TLS local é autoassinado e não é confiável por CA pública; isso é esperado no ambiente de demonstração, mas impede declarar PKI de produção.

## 5. Divergências documentais

- Não foi encontrada contradição de escopo entre `PRD.md`, `MVP.md` e `ARQUITETURA_ALVO.md`; as rotas e os componentes conferem.
- `docs/VALIDACAO_LOCAL.md` descreve um ambiente sem Docker; nesta sessão o Compose foi efetivamente construído e iniciado. O documento histórico não deve ser usado como estado atual sem atualização.
- Os scripts assumem IDs fixos de postos/guichês derivados do seed. O seed não declara IDs explícitos, mas a consulta ao banco confirmou: guichês 1/3 no posto 1 e 2/4 no posto 2. O `concurrent_calls.py` foi executado na F2 com PASS.
- A divergência acadêmica entre fator 0,3 e 0,4 do barema continua pendente de confirmação docente; não afeta o código.

## 6. Próximo passo

**F6 concluída.** O MVP está em estado de entrega/arguição:

1. Apresentar na ordem de `docs/ENTREGA.md`, deixando Dozzle iniciado e as 2 réplicas ativas.
2. Cada integrante deve conseguir explicar o fluxo completo (A18); usar a divisão sugerida no `docs/ENTREGA.md` apenas como apoio.
3. Declarar com transparência as limitações: AWS (A14) sem credencial válida, CI (A16) sem runner remoto, certificado TLS de desenvolvimento e acoplamento de rede entre projetos Compose no mesmo host.
4. Não reexecutar `docker compose down -v` nem operações AWS sem autorização explícita.
5. Se houver credencial AWS válida e repositório remoto autorizados, reabrir A14/A16 pontualmente; nenhum outro requisito está pendente.

**Não iniciar novas fases nem marcar A14/A16/A18 como PASSOU sem evidência real.**
