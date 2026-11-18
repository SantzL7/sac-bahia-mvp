# Guia de uso — OpenCode com DeepSeek no Windows

## 1. Preparar a pasta
Baixe o ZIP integrado do projeto e extraia em uma pasta de usuário, por exemplo `C:\Projetos\sac_bahia_mvp`. **Não abra o PowerShell em `C:\Windows\System32`** para criar projeto ou executar comandos npm.

Instale/confirme Docker Desktop, Node.js 22+, Python 3.10+ e Git. Confira com `docker compose version`, `node -v`, `py --version`, `git --version`.

## 2. Abrir o OpenCode no projeto
```powershell
cd C:\Projetos\sac_bahia_mvp
opencode
```
No OpenCode, use `/models` e **selecione um modelo DeepSeek já disponível no provedor conectado**. Caso não esteja conectado, siga `/connect` e as instruções do provedor da sua conta. **Não presuma que o DeepSeek é gratuito** ou que o ID do modelo é igual entre provedores. Se usar NVIDIA NIM ou outra API compatível, o provedor/modelo/endereço exatos dependem da configuração real; não inserir endpoints ou keys inventados neste repositório.

Documentação oficial: https://opencode.ai/docs/instructions/ ; https://opencode.ai/docs/models/ ; https://opencode.ai/docs/providers/

## 3. Ordem de leitura obrigatória da IA
1. `AGENTS.md` (regras persistentes da raiz)
2. `docs/PRD.md` e `docs/MVP.md` (produto e limite de escopo)
3. `docs/MATRIZ_BAREMA.md` e `docs/ACEITE.md` (requisitos e prova)
4. `docs/ARQUITETURA_ALVO.md` e `docs/ARQUITETURA.md` (desenho e código atual)
5. `openapi.yaml`, `compose.yaml`, `database/*.sql` (contratos efetivos)
6. `docs/PLANO_EXECUCAO.md` e `docs/PROGRESSO.md` (etapas e status)

## 4. Primeiro comando/prompt
Copie integralmente **Prompt 0** de `docs/PROMPTS_OPENCODE.md`. Não peça 'faça tudo' nem 'gere o projeto inteiro do zero' porque já existe código.

## 5. Testes locais mínimos
```powershell
py scripts/setup_env.py
npm install
npm run test:all
py -m compileall -q cliente-python scripts
docker compose config -q
docker compose up -d --build --scale api=2
docker compose ps
```
Após subir e confirmar health, instalar Python e seguir `README.md`. O `npm install` inicial cria `package-lock.json`: versionar este lockfile e depois preferir `npm ci` em builds quando validado.

Se PowerShell bloquear `npm.ps1`, use `npm.cmd` e `npx.cmd`, sem mudar a política de execução do Windows. Para CLI dentro do Python use `py` ou caminho `.venv\Scripts\python.exe`.

## 6. Fluxo seguro de mudanças
- Antes de cada tarefa, `git status` e `git diff`.
- Peça à IA apenas uma fase. Confira diff, rode testes, commit.
- Use mensagens de commit: `fix: corrigir idempotencia de emissao`, `test: validar concorrencia`, `docs: registrar evidencia de chaos`.
- Não conceda permissão global permanente para apagar pastas, derrubar volumes ou executar `terraform apply`.
- `docker compose down -v` **apaga dados**: somente com consentimento e backup se necessário.

## 7. O que evitar para reduzir tokens
AGENTS.md curto e rígido; arquivos MD separados por tema; prompts específicos; não passar PDF de 39 páginas em toda rodada; não pedir reescritas completas; usar `docs/PROGRESSO.md` para retomar sem repetir discussões.

## 8. Entrega
Antes da apresentação, executar todos os testes de `docs/ACEITE.md`, registrar evidências e ensaiar offline. Status inicial: não homologado (sem testes Docker comprovados aqui).
