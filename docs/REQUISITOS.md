# Requisitos congelados — SAC Bahia MVP

## Natureza do protótipo

Sistema de demonstração acadêmica de filas inspirado no domínio SAC Bahia. Os postos e tempos são **dados simulados**. Não consulta, representa ou modifica filas oficiais. O objetivo é demonstrar comunicação entre processos autônomos, consistência de transações e resiliência de falhas.

## Escopo funcional (RF)

| Código | Critério de aceite | Evidência |
|---|---|---|
| RF01 | CLI Python lista pelo menos dois postos | `python cliente-python/main.py --inseguro postos` |
| RF02 | CLI exibe `posto` e `tempo_espera_minutos` | `fila --posto 1` |
| RF03 | Emitir normal/prioritária retorna número único e token | `emitir` |
| RF04 | Cidadão consulta apenas a própria senha | `consultar --senha-id ... --token ...` |
| RF05 | Chamada por guichê impede dupla chamada e respeita prioridade | `chamar` + teste concorrente |
| RF06 | Finalização aceita somente senha CHAMADA | `finalizar` |
| RF07 | Eventos chegam ao cliente sem polling contínuo | `acompanhar` + outro terminal `chamar` |
| RF08 | Toda mutação gera evento em transação | SQL tabela `eventos` |
| RF09 | Integração Python/Node usa REST/OpenAPI | `openapi.yaml` + CLI |

Estados fixos `AGUARDANDO -> CHAMADA -> FINALIZADA`. Ordem de chamada: prioritárias primeiro; FIFO dentro da categoria. Sem reinício diário da sequência. Estimativa = pessoas à frente × média configurada / guichês ativos; `null` quando não houver guichês.

## Requisitos não funcionais (RNF)

- **RNF01:** duas réplicas da API atrás do Traefik; redes Docker e DNS interno, sem IP hardcoded.
- **RNF02:** PostgreSQL é fonte de verdade, transações e bloqueio de fila para emissão/chamada, unique constraint e idempotência.
- **RNF03:** eventos persistidos na mesma transação da operação; worker usa confirmação de publicação RabbitMQ e deduplicação.
- **RNF04:** RabbitMQ com filas principal, retry e DLQ; WebSocket notifica e cliente reconcilia por REST.
- **RNF05:** JWT com roles CIDADAO e ATENDENTE; autorizacão por ticket_id e posto_id; TLS de demonstração; segredos `.env` fora do Git; integração opcional AWS Secrets Manager comprovável.
- **RNF06:** logs JSON (API/Worker), `X-Correlation-ID` propagado, console Docker e Dozzle local.
- **RNF07:** Compose reproduzível, README, CI com validações, Terraform somente do Secrets Manager.
- **RNF08:** testes de carga de 50–100 requisições, interrupção de nó, reconciliação, rastreamento e DLQ.

## Escopo excluído

Frontend React, pagamento, dados oficiais SAC, gov.br, geolocalização, SMS, e-mail, IA, Kafka, Kubernetes, cluster PostgreSQL, cloud completa, prioridades 2:1, ETA por aprendizado de máquina, cadastro administrativo completo e autenticação de cidadãos reais.

## Critério de aceite da entrega

O README deve ser executável por terceiro em máquina com Docker Desktop e Python. Cada script deve fornecer resultado PASS/FAIL. O grupo apresentará logs, endpoints, mensagens RabbitMQ, prova de não duplicidade e duas instâncias. Registrar defeitos encontrados, comandos executados e prints sem expor credenciais ou JWTs.
