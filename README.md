# SAC Bahia — MVP de Sistemas Distribuídos (TDE Parte 2)

> **Protótipo acadêmico com dados simulados.** Não há integração nem vínculo com o SAC Bahia oficial. Repositório criado para demonstração de Sistemas Distribuídos, não para uso por cidadãos.

## O que está incluído

- Cliente **Python** (`requests` + `websocket-client`) com CLI e reconexão.
- API **Node.js/Express** REST documentada em [`openapi.yaml`](openapi.yaml), com duas réplicas.
- **Traefik**: entrada HTTPS/WSS, descoberta de serviços Docker e balanceamento.
- **PostgreSQL**: filas, senhas, guichês, transações, lock, idempotência, histórico/outbox.
- **Worker Node.js**: relay da outbox e consumo assíncrono.
- **RabbitMQ**: exchange de eventos, fila de trabalho, retentativa, DLQ e fanout WebSocket.
- **Segurança acadêmica**: tokens JWT assinados, papéis por posto/ticket, `.env` não versionado e opção de AWS Secrets Manager.
- **Rastreamento e teste**: Correlation ID, logs JSON, scripts Python de smoke, burst, WebSocket, concorrência, chaos, tracing e DLQ.

## Pré-requisitos

Docker Desktop com **Docker Compose v2** e Python 3.10+. A construção das imagens exige acesso à internet **na primeira execução**, pois serão baixadas imagens Docker e pacotes npm. Para demonstração offline, já deixe todas as imagens construídas. Sistema principal pode rodar 100% local, sem AWS.

### 1. Criar credenciais locais (uma vez)

Na pasta raiz do projeto:

```powershell
py scripts/setup_env.py
```

O script gera `.env` aleatório e exibe a senha do atendente. **Não compartilhe esse arquivo.** Se estiver no Linux, substitua `py` por `python3`.

### 2. Construir e iniciar os serviços

```powershell
docker compose up -d --build --scale api=2
docker compose ps
```

Se quiser ver logs agregados no navegador (Dozzle):

```powershell
docker compose --profile observabilidade up -d --scale api=2
```

Endereços:

| Serviço | URL |
|---|---|
| API, gateway HTTPS/WSS | `https://localhost:8443` |
| Health | `https://localhost:8443/health/ready` |
| Dozzle (opcional) | `http://localhost:8081` |
| RabbitMQ Management | `http://localhost:15672` (usuário `sac`, senha em `.env`) |

**TLS local:** Traefik usa certificado de desenvolvimento não confiável por padrão. O CLI tem `--inseguro` **somente para localhost**; isso desliga a validação do certificado e não deve ser replicado em produção. Em ambiente real configure uma autoridade confiável e remova `--inseguro`.

### 3. Instalar dependências do CLI no Windows (sem ativar script PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r cliente-python/requirements.txt
```

No Linux/macOS, utilize `python3 -m venv .venv` e `.venv/bin/python`.

### 4. Exercitar o MVP

```powershell
.\.venv\Scripts\python.exe cliente-python/main.py --inseguro postos
.\.venv\Scripts\python.exe cliente-python/main.py --inseguro fila --posto 1
.\.venv\Scripts\python.exe cliente-python/main.py --inseguro emitir --posto 1 --categoria NORMAL
```

O comando `emitir` retorna `senha_id` e `token` do cidadão. Cole **apenas em seu terminal local**:

```powershell
.\.venv\Scripts\python.exe cliente-python/main.py --inseguro consultar --senha-id "UUID_DA_SENHA" --token "TOKEN_DO_CIDADAO"
```

**Acompanhamento em tempo real**, num terminal separado:

```powershell
.\.venv\Scripts\python.exe cliente-python/main.py --inseguro acompanhar --posto 1 --senha-id "UUID_DA_SENHA" --token "TOKEN_DO_CIDADAO"
```

**Atendente**: obtenha um JWT com o usuário `atendente` e a senha exibida na etapa 1. O cliente solicitará a senha sem ecoá-la:

```powershell
.\.venv\Scripts\python.exe cliente-python/main.py --inseguro login --posto 1
```

Use o token de atendente retornado:

```powershell
.\.venv\Scripts\python.exe cliente-python/main.py --inseguro chamar --guiche 1 --token "TOKEN_ATENDENTE"
.\.venv\Scripts\python.exe cliente-python/main.py --inseguro finalizar --senha-id "UUID_CHAMADA" --token "TOKEN_ATENDENTE"
```

O terminal `acompanhar` deve receber `FILA_ATUALIZADA`, seguida de consulta REST somente quando há um evento (ou reconexão), **sem polling contínuo**.

## Testes de bancada

Execute com duas APIs e os serviços funcionando, usando o Python do ambiente virtual (nos comandos abaixo, substitua `py` pelo caminho do executável `.venv` caso necessário):

```powershell
py scripts/smoke.py
py scripts/burst.py
py scripts/concurrent_calls.py
py scripts/security_test.py
py scripts/websocket_test.py
py scripts/tracing.py
py scripts/dlq.py
py scripts/chaos.py
```

Os testes modificam **dados da demonstração**, não dados reais. A execução do `smoke` chama e finaliza senhas; faça os ensaios antes da apresentação. Em `burst.py`, são feitas **60 requisições simultâneas** e validados números/IDs únicos. `chaos.py` para uma réplica e depois a restaura. `tracing.py` dispara um evento com um UUID e procura o ID nos logs da API e Worker. `dlq.py` injeta mensagem inválida controlada, aguarda as retentativas e valida a fila DLQ pelo RabbitMQ Management. Não executar esses scripts contra produção.

**Falha parcial do broker** (opcional, demonstrável):

```powershell
docker compose stop rabbitmq
# Emita uma senha no cliente: a transação deve persistir mesmo sem notificação.
docker compose logs --tail=30 worker
docker compose start rabbitmq
# Aguarde reconexão; acompanhe eventos/logs.
```

Se o banco ou Traefik cair, a aplicação não oferece redundância para esses nós; é necessário mostrar erro/degradação controlada, não prometer alta disponibilidade geral.

**Comprovação das duas instâncias:**

```powershell
docker compose ps api
docker compose logs --tail=50 api
```

**Teste de sintaxe e lógica sem serviços:**

```powershell
npm install
npm run test:all
```

O `npm install` também cria `package-lock.json`, que deve ser versionado após a primeira instalação para garantir dependências transitivas reproduzíveis. As dependências diretas já estão fixadas em `package.json`.

## AWS Secrets Manager — integração mínima opcional

O sistema **não depende da AWS para operar localmente**. Para atender à exigência específica de isolamento de credenciais em um gerenciador real, há integração SDK e Terraform mínimo, **não uma infraestrutura AWS completa**.

1. Com uma conta AWS autorizada, entre em `infra/terraform/` e execute `terraform init`, `terraform plan` e, **somente após verificar custo/permissões**, `terraform apply`.
2. O output `secret_arn` indica o segredo criado. No console AWS Secrets Manager, atribua um valor JSON com as chaves `JWT_SECRET` e `STAFF_PASSWORD`, preferencialmente usando os mesmos valores já gerados no `.env` para compatibilidade com os scripts de teste. **Não armazene o valor em arquivos versionados ou no estado Terraform.**
3. Configure `AWS_SECRET_ID=<ARN>` no `.env`; para credenciais AWS locais via perfil, defina `AWS_CONFIG_DIR` para a pasta `.aws` do host e `AWS_PROFILE`, se necessário. Inicie com `docker compose -f compose.yaml -f compose.aws.yaml up -d --build --scale api=2`.
4. Prove a leitura com logs `aws_secrets_loaded` da API. Utilize perfil AWS com permissão somente de `secretsmanager:GetSecretValue` para o ARN. Ao terminar, remova recursos com cuidado e acompanhe eventuais cobranças.

O arquivo `compose.aws.yaml` monta a configuração AWS do host como somente leitura para o usuário `node`. Dependendo do sistema operacional/ACLs, ajuste o caminho/permissões. **Não publique chaves AWS nem imagens de tokens nos anexos da entrega.**

## Organização e critérios

- `docs/REQUISITOS.md`: RF/RNF e critérios de aceite.
- `docs/ARQUITETURA.md`: fluxos, modelo de consistência, limites, DNS e decisões.
- `docs/ENTREGA.md`: evidências exigidas C1–C8, divisão e roteiro da apresentação.
- `openapi.yaml`: contrato REST/IDL.
- `.github/workflows/ci.yml`: validação sintática, testes e build via CI.

### Reset do laboratório

```powershell
docker compose down
```

**Não execute `docker compose down -v` antes de concluir as evidências:** ele elimina os volumes com senhas/eventos e configurações do broker. Use `down -v` somente se realmente quiser apagar o banco simulado para ensaio limpo.

## Estado de validação deste pacote

O código foi produzido como MVP executável em configuração Docker. **No ambiente de geração não há Docker nem acesso ao registro npm**, portanto não foi possível iniciar o Compose, instalar as dependências Node ou executar testes de integração fim a fim. As verificações de sintaxe JavaScript, compilação Python e testes unitários do núcleo estão disponíveis e devem ser executadas/confirmadas na máquina do grupo. Não classificar como 'validado em produção' ou como 'pronto para apresentação' até passar nos testes de bancada.
