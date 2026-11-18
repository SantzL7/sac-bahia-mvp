# AGENTS.md — Política obrigatória para OpenCode/DeepSeek

**Projeto:** SAC Bahia, protótipo acadêmico de Sistemas Distribuídos, com dados simulados. Não é sistema oficial. **Código-base já existe:** antes de gerar qualquer coisa, auditar.

## Prioridade da documentação
1. `docs/PRD.md` — propósito e requisitos.
2. `docs/MVP.md` — limite estrito do escopo.
3. `docs/MATRIZ_BAREMA.md` e `docs/ACEITE.md` — comprovação exigida C1–C8.
4. `docs/ARQUITETURA_ALVO.md` — desenho simplificado e limites.
5. `openapi.yaml`, `compose.yaml`, `database/*.sql` — contratos/estrutura atuais.
6. `docs/PLANO_EXECUCAO.md` e `docs/PROGRESSO.md` — ordem e estado factual.

## Regras inegociáveis
- **Não desenvolver tudo de uma vez.** Executar somente a etapa F0–F6 explicitamente solicitada; primeira tarefa é F0 auditoria.
- Não criar frontend React, Kafka, Redis, Kubernetes, Docker Swarm, cloud AWS completa, novos módulos ou tabelas por iniciativa própria.
- Manter Node/Express + Python CLI + PostgreSQL + RabbitMQ + Worker + Traefik + Compose.
- Não quebrar `openapi.yaml`, cliente Python, idempotência, lock, segurança ou consumo WebSocket.
- Preferir diff mínimo e teste reproduzível; não reescrever arquivos enormes sem justificativa.
- PostgreSQL = verdade; mutação da senha e outbox na mesma transação; worker idempotente.
- Não publicar JWT, senhas, `.env`, AWS keys, logs com credenciais ou resultados inventados.
- Não executar `docker compose down -v`, `terraform apply/destroy`, exclusão de recursos ou operações de custo sem confirmação explícita.
- **Sempre reportar:** (1) requisito, (2) arquivos modificados, (3) comando executado, (4) resultado PASSOU/FALHOU/NÃO EXECUTADO, (5) pendência e próximo passo.
- Atualizar `docs/PROGRESSO.md`; não marcar `docs/ACEITE.md` como aprovado sem evidência real.

## Comandos úteis
- JS: `npm run test:all` (se dependências disponíveis).
- Python: `py -m compileall -q cliente-python scripts` (Windows) ou `python3 -m compileall -q cliente-python scripts`.
- Docker: `py scripts/setup_env.py` e `docker compose config -q`; depois `docker compose up -d --build --scale api=2`.
- Ver `README.md` para testes E2E.

**Primeira interação com a IA:** Prompt 0 em `docs/PROMPTS_OPENCODE.md`.
