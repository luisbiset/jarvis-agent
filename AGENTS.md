# Manutenção do Jarvis Agent

Este repositório é a fonte central do Jarvis Agent e reúne os plugins, skills e perfis de subagentes pessoais da SESAB.

## Regras

- Nunca grave credenciais, tokens, URLs privadas adicionais ou dados clínicos/faturamento reais.
- Preserve `plugins/redmine-agent/.mcp.json` fora do Git; mantenha apenas o exemplo anonimizado.
- Não crie commit, tag, remote ou push sem solicitação explícita do proprietário.
- Evite cópias paralelas em `~/plugins` e links de skills fora do marketplace central.
- Ao alterar uma skill, valide seu frontmatter e seu `agents/openai.yaml`.
- Ao alterar um plugin, valide o manifest, atualize somente o cachebuster e reinstale pelo marketplace `codex-agents`.
- Não execute operações reais no Redmine, banco, WildFly, Docker ou ambientes compartilhados durante testes deste projeto.

## Validação

Execute, a partir da raiz:

```bash
python3 scripts/validate.py
python3 scripts/doctor.py --strict
python3 scripts/smoke_install.py
node plugins/redmine-agent/scripts/server.mjs --self-test
```

O autoteste do Redmine usa somente um servidor HTTP temporário em `127.0.0.1` e dados fictícios.
O eval com `scripts/run_evals.py --live` é opcional e não deve ser executado em manutenção rotineira, pois consome uma chamada do modelo.
