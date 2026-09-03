# Jarvis Agent V3.1

Projeto-fonte do Jarvis Agent: plugins, skills e agentes pessoais usados no Codex.

## Instalação

Consulte o [guia completo de instalação](INSTALL.md) para preparar o ambiente, configurar o Redmine com segurança, instalar os agentes e plugins globalmente e validar a instalação.

## Guia de uso

Comece pelos [comandos básicos para economizar créditos](docs/COMANDOS_BASICOS.md). Consulte também o [guia rápido por skill](docs/GUIA_RAPIDO.md) ou, para arquitetura, fluxos e diagnóstico, o [guia completo](docs/GUIA_COMPLETO.md).

## Estrutura

- `plugins/redmine-agent/`: plugin de integração e workflows do Redmine.
- `plugins/sfa-agent/`: coordenador de desenvolvimento do SFA.
- `plugins/aghuse-agent/`: coordenador de desenvolvimento do AGHUse.
- `agents/sfa_frontend.toml`: especialista Angular do SFA.
- `agents/sfa_backend.toml`: especialista Java/Spring do SFA.
- `agents/sfa_database.toml`: especialista Oracle/PostgreSQL do SFA.
- `agents/sfa_tests.toml`: especialista de testes Java e Angular do SFA.
- `agents/aghuse_frontend.toml`: especialista JSF/PrimeFaces do AGHUse.
- `agents/aghuse_backend.toml`: especialista Java EE/EJB do AGHUse.
- `agents/aghuse_database.toml`: especialista Oracle/PostgreSQL do AGHUse.
- `agents/aghuse_tests.toml`: especialista em testes unitários exclusivamente de ONs e RNs do AGHUse.
- `agents/aghuse_analyst.toml`: analista somente leitura de tarefas e requisitos do AGHUse.
- `agents/sesab_reviewer.toml`: revisão final independente e somente leitura.
- `agents/qa_homologacao.toml`: execução de roteiros e evidências de homologação em tela.
- `.agents/plugins/marketplace.json`: marketplace local deste projeto.
- `scripts/validate.py`: valida manifests, agents, skills, evals e segredos literais.
- `scripts/doctor.py`: diagnostica instalação, duplicidades e MCP sem mostrar credenciais; `--strict` falha em inconsistências.
- `scripts/install.sh`: instala agents e plugins a partir desta fonte central; aceita `--dry-run`.
- `scripts/smoke_install.py`: prova a instalação em um `CODEX_HOME` temporário e vazio.
- `scripts/run_evals.py`: carrega os contratos de roteamento e, com `--live`, avalia decisões usando `codex exec`.
- `config/AGENTS.md`: política global instalada no Codex para aplicar métricas em todas as tarefas.
- `scripts/jarvis_runtime.py`: decide reasoning adaptativo, aplica budgets por complexidade e persiste estado, tentativas, escaladas, findings, gates e métricas históricas da V3.1 em JSONL e SQLite.
- `contracts/reasoning-policy.json`: pesos, thresholds, levels e budgets versionados do Adaptive Reasoning.
- `contracts/`: schemas, políticas, fronteiras de papéis, padrões de tarefa e versão comportamental.
- `docs/TOPOLOGY.md`: topologia gerada automaticamente a partir dos manifests, agents e skills.
- `docs/TELEMETRIA.md`: comandos e contrato operacional da telemetria local V3.
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

O argumento legado abaixo continua aceito, mas a instalação padrão já copia os agentes:

~~~bash
./scripts/install.sh --copy-agents
~~~

Equivalente manual:

```bash
codex plugin marketplace add "$PWD"
codex plugin add redmine-agent@codex-agents
codex plugin add sfa-agent@codex-agents
codex plugin add aghuse-agent@codex-agents
```

## Instalação dos subagentes

Os arquivos TOML podem ser copiados para `.codex/agents/` de um projeto ou para `~/.codex/agents/` quando devem ficar disponíveis globalmente. O instalador sempre cria arquivos independentes em `~/.codex/agents/`; execute-o novamente após alterar um agente e abra uma conversa nova para recarregar os perfis. Não adicione esses arquivos ao Git corporativo sem uma decisão explícita da equipe.

Depois de alterar um plugin, valide-o, atualize o cachebuster e reinstale-o antes de testar em uma conversa nova.

## Qualidade e diagnóstico

```bash
python3 scripts/validate.py
python3 scripts/doctor.py --strict
python3 scripts/smoke_install.py
node plugins/redmine-agent/scripts/server.mjs --self-test
```

Os casos em `evals/routing-cases.json` documentam quais skills e agentes devem ou não ser acionados para pedidos representativos. A validação padrão é determinística e não acessa Redmine, banco ou ambientes reais.

## Protocolo Jarvis V3

A V3.1 classifica complexidade, risco e modo, calcula reasoning `INSTANT`/`MEDIUM`/`HIGH` por sinais objetivos e permite somente uma escalada `MEDIUM → HIGH` dentro do budget. Budgets padrão limitam tarefas `TRIVIAL`, `LOCALIZED`, `TRANSVERSAL` e `CRITICAL` a 1, 2, 4 e 6 agentes e a 1, 3, 5 e 6 chamadas de modelo. O contrato completo está em [contracts/protocol.md](contracts/protocol.md), a policy em [contracts/reasoning-policy.json](contracts/reasoning-policy.json) e o handoff em [contracts/handoff.schema.json](contracts/handoff.schema.json).

O runtime é usado em todas as tarefas quando estiver disponível; tarefas simples continuam sem subagentes e usam somente a classificação e o registro mínimos:

```bash
python3 scripts/jarvis_runtime.py init \
  --task-id TASK-FICTICIA \
  --complexity LOCALIZED \
  --risk-class MEDIUM \
  --operational-mode ASSISTED_AUTOPILOT \
  --task-type BACKEND \
  --estimated-files 3 \
  --tests-required \
  --complexity-score 3

python3 scripts/jarvis_runtime.py transition --run-dir .jarvis/runs/<run_id> \
  --to PLAN_APPROVED --reason "pedido direto e escopo inequívoco"
python3 scripts/jarvis_runtime.py invocation-start --run-dir .jarvis/runs/<run_id> \
  --agent aghuse_backend --stage IMPLEMENTING --reasoning-effort medium
python3 scripts/jarvis_runtime.py invocation-finish --run-dir .jarvis/runs/<run_id> \
  --invocation-id <invocation_id> --status OK --agent-result USEFUL \
  --input-tokens 1000 --cached-input-tokens 400 --output-tokens 250 --credits 1.2
python3 scripts/jarvis_runtime.py handoff --run-dir .jarvis/runs/<run_id>
python3 scripts/jarvis_runtime.py summary --run-dir .jarvis/runs/<run_id>
python3 scripts/jarvis_runtime.py dashboard
python3 scripts/jarvis_runtime.py report-cost --last 20 --group-by agent
python3 scripts/jarvis_runtime.py export --format json --output /tmp/jarvis-telemetry.json
```

O runtime calcula automaticamente horários e durações. Tokens e créditos são valores observados fornecidos pelo executor; quando indisponíveis, permanecem zero em vez de serem estimados. O banco histórico fica em `.jarvis/telemetry/jarvis.db`. Todo `.jarvis/` é local e ignorado pelo Git; conteúdo clínico, faturamento real, credenciais e URLs privadas são recusados.

O eval ao vivo é opcional porque consome uma execução do modelo:

~~~bash
python3 scripts/run_evals.py --live
python3 scripts/run_evals.py --live --case aghuse-new-rule --model gpt-5.6-luna
python3 scripts/run_evals.py --live --canary --save-results /tmp/jarvis-eval-v2
python3 scripts/run_evals.py --result-dir /tmp/jarvis-eval-v2 --compare-baseline
~~~

O modo ao vivo pede somente uma decisão estruturada de roteamento, usa sandbox somente leitura e proíbe chamadas externas e alterações.

## Formato de handoff

Coordenadores e especialistas preservam o handoff schema 2.0 dentro do runtime V3: run/version, estágio, classificações, requisitos, arquivos com owner/finalidade, contratos, decisões com provenance, validações executadas e não executadas, riscos, limitações, blockers, stop reason e próximo responsável.
