# Jarvis Agent

Projeto-fonte do Jarvis Agent: plugins, skills e agentes pessoais usados no Codex.

## Instalação

Consulte o [guia completo de instalação](INSTALL.md) para preparar o ambiente, configurar o Redmine com segurança, instalar os agentes e plugins globalmente e validar a instalação.

## Guia de uso

Consulte o [guia completo do Jarvis Agent SESAB](plugins/sesab-orchestrator/skills/sesab-orchestration/references/guia-de-uso.md) para escolher skills e especialistas, executar o fluxo Redmine → implementação → testes → revisão → homologação, usar prompts prontos e diagnosticar a instalação.

## Estrutura

- `plugins/redmine-agent/`: plugin de integração e workflows do Redmine.
- `plugins/sfa-agent/`: coordenador de desenvolvimento do SFA.
- `plugins/aghuse-agent/`: coordenador de desenvolvimento do AGHUse.
- `plugins/sesab-orchestrator/`: orquestrador principal do Redmine, SFA e AGHUse.
- `agents/sfa_frontend.toml`: especialista Angular do SFA.
- `agents/sfa_backend.toml`: especialista Java/Spring do SFA.
- `agents/sfa_database.toml`: especialista Oracle/PostgreSQL do SFA.
- `agents/sfa_tests.toml`: especialista de testes Java e Angular do SFA.
- `agents/aghuse_frontend.toml`: especialista JSF/PrimeFaces do AGHUse.
- `agents/aghuse_backend.toml`: especialista Java EE/EJB do AGHUse.
- `agents/aghuse_database.toml`: especialista Oracle/PostgreSQL do AGHUse.
- `agents/aghuse_tests.toml`: especialista em testes unitários do AGHUse.
- `agents/aghuse_analyst.toml`: analista somente leitura de tarefas e requisitos do AGHUse.
- `agents/sesab_orchestrator.toml`: orquestrador principal dos dois sistemas.
- `agents/sesab_reviewer.toml`: revisão final independente e somente leitura.
- `agents/qa_homologacao.toml`: roteiros e execução de homologação em tela.
- `.agents/plugins/marketplace.json`: marketplace local deste projeto.
- `scripts/validate.py`: valida manifests, agents, skills, evals e segredos literais.
- `scripts/doctor.py`: diagnostica instalação, duplicidades e MCP sem mostrar credenciais; `--strict` falha em inconsistências.
- `scripts/install.sh`: instala agents e plugins a partir desta fonte central; aceita `--dry-run` e `--copy-agents`.
- `scripts/smoke_install.py`: prova a instalação em um `CODEX_HOME` temporário e vazio.
- `scripts/run_evals.py`: carrega os contratos de roteamento e, com `--live`, avalia decisões usando `codex exec`.
- `evals/routing-cases.json`: casos de avaliação de roteamento e segurança.
- `plugins/redmine-agent/src/`: cliente HTTP, ferramentas e protocolo MCP modularizados.
- `plugins/redmine-agent/tests/`: testes de contrato, erros HTTP, timeout, redaction e ferramentas.

## Segurança

O arquivo `plugins/redmine-agent/.mcp.json` é local e ignorado pelo Git porque contém configuração de ambiente. Use `.mcp.json.example` como modelo. A chave do Redmine deve existir somente na variável `REDMINE_API_KEY`; nunca a grave neste repositório.

## Instalação dos plugins

Na raiz deste projeto, prefira a instalação idempotente:

```bash
./scripts/install.sh
```

Para conferir previamente os comandos sem alterar a instalação:

~~~bash
./scripts/install.sh --dry-run
~~~

Para uma instalação portátil sem links simbólicos:

~~~bash
./scripts/install.sh --copy-agents
~~~

Equivalente manual:

```bash
codex plugin marketplace add "$PWD"
codex plugin add redmine-agent@codex-agents
codex plugin add sfa-agent@codex-agents
codex plugin add aghuse-agent@codex-agents
codex plugin add sesab-orchestrator@codex-agents
```

## Instalação dos subagentes

Os arquivos TOML podem ser copiados para `.codex/agents/` de um projeto ou para `~/.codex/agents/` quando devem ficar disponíveis globalmente. O instalador usa links simbólicos por padrão para refletir atualizações desta fonte central; use `--copy-agents` ao transportar a instalação para outra máquina. Não adicione esses arquivos ao Git corporativo sem uma decisão explícita da equipe.

Depois de alterar um plugin, valide-o, atualize o cachebuster e reinstale-o antes de testar em uma conversa nova.

## Qualidade e diagnóstico

```bash
python3 scripts/validate.py
python3 scripts/doctor.py --strict
python3 scripts/smoke_install.py
node plugins/redmine-agent/scripts/server.mjs --self-test
```

Os casos em `evals/routing-cases.json` documentam quais skills e agentes devem ou não ser acionados para pedidos representativos. A validação padrão é determinística e não acessa Redmine, banco ou ambientes reais.

O eval ao vivo é opcional porque consome uma execução do modelo:

~~~bash
python3 scripts/run_evals.py --live
python3 scripts/run_evals.py --live --case aghuse-new-rule --model gpt-5.6-luna
~~~

O modo ao vivo pede somente uma decisão estruturada de roteamento, usa sandbox somente leitura e proíbe chamadas externas e alterações.

## Formato de handoff

Coordenadores e especialistas devem consolidar: resultado, evidências, arquivos, contrato afetado, validações, riscos, limitações e handoff pendente.
