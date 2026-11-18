# PRD — Sistema Distribuído de Filas SAC Bahia (MVP acadêmico)

**Versão:** 1.0 | **Status:** especificação congelada para implementação assistida | **Data:** 17/11/2026

## 1. Contexto
Trabalho TDE Parte 2 de Sistemas Distribuídos (UNIFAN). O protótipo utiliza **postos e dados simulados**. Não possui vínculo, credenciais ou integração com o SAC Bahia oficial. O objetivo é comprovar comunicação em rede, concorrência, eventos em tempo real, resiliência, DNS/roteamento, segurança, observabilidade e execução reproduzível, não construir produto de atendimento público.

**Fonte de exigências:** `Barema Geral Unificado ... TDE Parte 2`, avaliação Parte 1 da Equipe 4 e proposta REST do professor. **Fonte da implementação:** arquivos atuais do repositório. As decisões deste PRD foram simplificadas com base no escopo de entrega.

## 2. Problema e proposta de valor
Cidadãos simulados precisam verificar a fila de um posto, emitir senha e receber atualizações sem polling HTTP repetitivo. Atendentes precisam chamar e finalizar senhas, mesmo quando há múltiplos acessos concorrentes. A arquitetura prova que processos distintos cooperam por rede sem compartilhar memória.

## 3. Usuários/atores
- **Leitor público:** lista postos e consulta estimativa agregada.
- **Cidadão simulado:** emite senha NORMAL/PRIORITARIA; recebe token do próprio ticket; consulta/acompanhamento permitido somente da própria senha.
- **Atendente:** autentica-se e chama/finaliza senhas apenas do posto autorizado.
- **Worker:** publica eventos pendentes e processa mensagens; não altera arbitrariamente estado definitivo das senhas.

Não há cadastro de usuário completo, painel administrativo ou integração governamental.

## 4. Jornada principal e critérios de sucesso
1. Python lista pelo menos dois postos simulados e consulta fila via HTTP JSON.
2. Python emite senha com `Idempotency-Key`; Node.js grava senha + evento na mesma transação PostgreSQL.
3. Cliente acompanha a própria senha por WebSocket; API envia aviso quando a fila muda. O estado definitivo é reconciliado por REST após o evento ou reconexão.
4. Atendente recebe JWT de demonstração, chama a próxima senha e a finaliza. Cada mudança publica evento assíncrono via RabbitMQ.
5. Duas APIs atendem por Traefik e usam o mesmo banco; 50–100 requisições concorrentes não geram duplicidade.
6. Testes comprovam falha parcial, carga e correlação de logs.

**Definição de sucesso:** todos os itens críticos de `docs/ACEITE.md` passam na máquina de apresentação e as evidências são registradas. Planejamento não equivale a teste aprovado.

## 5. Requisitos funcionais (escopo fechado)
| ID | Requisito | Aceite |
|---|---|---|
| RF01 | Listar postos | Cliente exibe postos simulados cadastrados |
| RF02 | Consultar fila/ETA | Retorna `posto`, `tempo_espera_minutos`, contagem e horário |
| RF03 | Emitir senha | Gera UUID, número único por fila, categoria e token, respeitando idempotência |
| RF04 | Consultar/acompanhamento | Somente token autorizado recupera detalhes da própria senha |
| RF05 | Chamar próxima senha | Atendente com posto válido chama 1 senha AGUARDANDO, sem chamada concorrente duplicada |
| RF06 | Finalizar atendimento | Transição CHAMADA → FINALIZADA, persistida, sem repetir transição |
| RF07 | Notificar por eventos | Broker + Worker + WS; sem polling contínuo |
| RF08 | Registrar histórico/outbox | Cada mutação cria evento durável na mesma transação |
| RF09 | Integração heterogênea | Python (`requests`, `websocket-client`) consome Node/Express por contrato |

## 6. Requisitos não funcionais
| ID | Requisito | Prova |
|---|---|---|
| RNF01 | Múltiplos processos autônomos | `docker compose ps`, logs e tráfego de rede |
| RNF02 | Consistência e concorrência | Locks PostgreSQL, constraints UNIQUE, testes de burst e chamadas |
| RNF03 | Eventos resilientes | Outbox, confirmações, retries limitados e DLQ |
| RNF04 | Escalabilidade e roteamento | 2 instâncias stateless e Traefik com DNS interno Docker |
| RNF05 | Segurança | TLS local, JWT validado, RBAC, `.env` não versionado e prova de segredo gerenciado quando autorizada |
| RNF06 | Observabilidade | Logs JSON, `X-Correlation-ID` propagado e consulta de logs agregados |
| RNF07 | Reprodutibilidade | Compose + scripts de configuração + README + CI |
| RNF08 | Falhas controladas | Timeout finito, retry/backoff, falha parcial e circuit breaker testado ou lacuna explicitamente registrada |

## 7. Regras de negócio
- Estados: `AGUARDANDO -> CHAMADA -> FINALIZADA`; não permitir retrocesso.
- Categorias: `NORMAL` e `PRIORITARIA`; prioridade antes da normal e FIFO na mesma categoria **para o protótipo**, não uma regra oficial do SAC.
- Senha numerada monotonicamente por fila, sem reinício diário no MVP.
- Um guichê ativo atende senha do mesmo posto; autenticação ATENDENTE deve validar posto.
- ETA simulado: pessoas à frente × média fixa de atendimento / guichês ativos; sem guichês, `null`.
- Requisições de emissão com a mesma `Idempotency-Key` e mesmo payload retornam o mesmo resultado; chave repetida com payload diferente deve retornar HTTP 409.
- PostgreSQL é a fonte de verdade. WebSocket é aviso efêmero; cliente reconcilia por REST após notificação e reconexão.
- Entrega de mensagens pode ser pelo menos uma vez; consumidores devem deduplicar efeitos persistentes.

## 8. Não objetivos / fora do escopo
React, dashboard visual, login público, SMS, email, QR code, geolocalização, recomendação de rotas, IA/ML, integração SAC real, gov.br, filas multiatendimento avançadas, pagamentos, Redis, Kafka, Kubernetes, deploy AWS completo, RDS/ALB/ASG/ElastiCache, aplicativo mobile, refresh tokens e funcionalidades administrativas extensas.

## 9. Restrições e riscos
- A demonstração principal deve funcionar localmente, inclusive sem internet após imagens/dependências previamente baixadas.
- Docker e testes integrados não foram comprovados no ambiente de geração; **não afirmar que a entrega está homologada**.
- A exigência específica do professor cita Secrets Manager. A AWS é integração mínima isolada; sem credenciais/custo autorizado, documentar bloqueio e não simular aprovação.
- Há inconsistência no barema entre conversão `×0,3` e ficha `×0,4` para nota institucional de 3,0; confirmar com o professor.
- A documentação da proposta antiga limita squads a 3–4 alunos, mas a Equipe 4 foi avaliada com cinco na Parte 1; manter a composição apenas com confirmação docente.

## 10. Entregáveis
Código no GitHub; `README.md`; `openapi.yaml`; `compose.yaml`; schema/seed; cliente Python; testes; documentação arquitetural e matriz C1–C8; evidências de execução e roteiro da apresentação. Ver `docs/PLANO_EXECUCAO.md` e `docs/ACEITE.md`.
