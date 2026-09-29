# Jarvis Agent V3.1

Projeto-fonte do Jarvis Agent: plugins, skills e agentes pessoais usados no Codex.

## InstalaÃ§Ã£o

Consulte o [guia completo de instalaÃ§Ã£o](docs/INSTALL.md) para preparar o ambiente, configurar o Redmine com seguranÃ§a, instalar os agentes e plugins globalmente e validar a instalaÃ§Ã£o.

## Guia de uso

Comece pelos [comandos bÃ¡sicos para economizar crÃ©ditos](docs/COMANDOS_BASICOS.md). Consulte tambÃ©m o [guia rÃ¡pido por skill](docs/GUIA_RAPIDO.md) ou, para arquitetura, fluxos e diagnÃ³stico, o [guia completo](docs/GUIA_COMPLETO.md).

## Estrutura

- `plugins/redmine-agent/`: plugin de integraÃ§Ã£o e workflows do Redmine.
- `plugins/sfa-agent/`: coordenador de desenvolvimento do SFA.
- `plugins/aghuse-agent/`: coordenador de desenvolvimento do AGHUse.
- `agents/sfa_frontend.toml`: especialista Angular do SFA.
- `agents/sfa_backend.toml`: especialista Java/Spring do SFA.
- `agents/sfa_database.toml`: especialista Oracle/PostgreSQL do SFA.
- `agents/sfa_tests.toml`: especialista de testes Java e Angular do SFA.
- `agents/aghuse_frontend.toml`: especialista JSF/PrimeFaces do AGHUse.
- `agents/aghuse_backend.toml`: especialista Java EE/EJB do AGHUse.
- `agents/aghuse_banco.toml`: especialista Oracle/PostgreSQL do AGHUse.
- `agents/aghuse_testes.toml`: especialista em testes unitÃ¡rios exclusivamente de ONs e RNs do AGHUse.
- `agents/aghuse_analise.toml`: analista somente leitura de tarefas e requisitos do AGHUse.
- `agents/aghuse_revisor.toml`: revisÃ£o final independente e somente leitura.
- `agents/aghuse_qualidade.toml`: execuÃ§Ã£o de roteiros e evidÃªncias de homologaÃ§Ã£o em tela.
- `.agents/plugins/marketplace.json`: marketplace local deste projeto.
- `scripts/validate.py`: valida manifests, agents, skills, evals e segredos literais.
- `scripts/doctor.py`: diagnostica instalaÃ§Ã£o, duplicidades e MCP sem mostrar credenciais; `--strict` falha em inconsistÃªncias.
- `scripts/install.sh`: instala agents e plugins a partir desta fonte central; aceita `--dry-run`.
- `scripts/smoke_install.py`: prova a instalaÃ§Ã£o em um `CODEX_HOME` temporÃ¡rio e vazio.
- `scripts/run_evals.py`: carrega os contratos de roteamento e, com `--live`, avalia decisÃµes usando `codex exec`.
- `config/AGENTS.md`: polÃ­tica global instalada no Codex para aplicar mÃ©tricas em todas as tarefas.
- `scripts/jarvis_runtime.py`: decide reasoning adaptativo, aplica budgets por complexidade e persiste estado, tentativas, escaladas, findings, gates e mÃ©tricas histÃ³ricas da V3.1 em JSONL e SQLite.
- `scripts/jarvis_rag.py`: indexa e consulta conhecimento local incremental sem chamada de modelo.
- `rag/`: chunking estrutural, seguranÃ§a, Ã­ndice SQLite, retrieval, ranking e interfaces de embeddings/vector store.
- `contracts/reasoning-policy.json`: pesos, thresholds, levels e budgets versionados do Adaptive Reasoning.
- `contracts/`: schemas, polÃ­ticas, fronteiras de papÃ©is, padrÃµes de tarefa e versÃ£o comportamental.
- `docs/TOPOLOGY.md`: topologia gerada automaticamente a partir dos manifests, agents e skills.
- `docs/TELEMETRIA.md`: comandos e contrato operacional da telemetria local V3.
- `docs/RAG.md`: arquitetura, seguranÃ§a, comandos e limites do RAG local-first.
- `evals/routing-cases.json`: casos de avaliaÃ§Ã£o de roteamento e seguranÃ§a.
- `plugins/redmine-agent/src/`: cliente HTTP, ferramentas e protocolo MCP modularizados.
- `plugins/redmine-agent/tests/`: testes de contrato, erros HTTP, timeout, redaction e ferramentas.

## SeguranÃ§a

O arquivo `plugins/redmine-agent/.mcp.json` Ã© local e ignorado pelo Git porque contÃ©m configuraÃ§Ã£o de ambiente. Use `.mcp.json.example` como modelo. A chave do Redmine deve existir somente na variÃ¡vel `REDMINE_API_KEY`; nunca a grave neste repositÃ³rio.

## InstalaÃ§Ã£o dos plugins

Na raiz deste projeto, prefira a instalaÃ§Ã£o idempotente:

```bash
./scripts/install.sh
```

Para conferir previamente os comandos sem alterar a instalaÃ§Ã£o:

~~~bash
./scripts/install.sh --dry-run
~~~

O argumento legado abaixo continua aceito, mas a instalaÃ§Ã£o padrÃ£o jÃ¡ copia os agentes:

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

## InstalaÃ§Ã£o dos subagentes

Os arquivos TOML podem ser copiados para `.codex/agents/` de um projeto ou para `~/.codex/agents/` quando devem ficar disponÃ­veis globalmente. O instalador sempre cria arquivos independentes em `~/.codex/agents/`; execute-o novamente apÃ³s alterar um agente e abra uma conversa nova para recarregar os perfis. NÃ£o adicione esses arquivos ao Git corporativo sem uma decisÃ£o explÃ­cita da equipe.

Depois de alterar um plugin, valide-o, atualize o cachebuster e reinstale-o antes de testar em uma conversa nova.

## Qualidade e diagnÃ³stico

TambÃ©m Ã© possÃ­vel usar a interface unificada:

```bash
python3 scripts/jarvis.py auditar
python3 scripts/jarvis.py resumo-git
python3 scripts/jarvis.py simular --task-id TESTE --task-type SECURITY --security-sensitive
python3 scripts/jarvis.py simular-redmine --task-id 55315
python3 scripts/jarvis.py rag search --query "frequencia aprazamento"
python3 scripts/jarvis.py executar dashboard
python3 scripts/jarvis.py aghuse-analisar --project /caminho/do/aghuse --requisito "Permitir alterar o campo X na tela Y"
```

Antes de publicar uma alteraÃ§Ã£o, use os comandos somente leitura:

```bash
python3 scripts/jarvis_guard.py audit
python3 scripts/jarvis_guard.py git-summary
```

O primeiro recusa credenciais, URLs privadas e identificadores clÃ­nicos detectÃ¡veis; o segundo mostra branch, commit e arquivos pendentes sem executar commit ou push.
Na busca do RAG, use tambÃ©m `--branch-filter` e `--source-type-filter` para restringir a origem do conhecimento.

Para habilitar a mesma auditoria automaticamente antes de cada commit nesta cÃ³pia:

```bash
git config core.hooksPath .githooks
```

Para simular uma tarefa sem criar estado, modificar arquivos ou acessar serviÃ§os externos:

```bash
python3 scripts/jarvis_simulate.py --task-id TESTE --task-type SECURITY --security-sensitive
```

```bash
python3 scripts/validate.py
python3 scripts/doctor.py --strict
python3 scripts/smoke_install.py
node plugins/redmine-agent/scripts/server.mjs --self-test
```

Os casos em `evals/routing-cases.json` documentam quais skills e agentes devem ou nÃ£o ser acionados para pedidos representativos. A validaÃ§Ã£o padrÃ£o Ã© determinÃ­stica e nÃ£o acessa Redmine, banco ou ambientes reais.

## Protocolo Jarvis V3

A V3.1 classifica complexidade, risco e modo, calcula reasoning `INSTANT`/`MEDIUM`/`HIGH` por sinais objetivos e permite somente uma escalada `MEDIUM â†’ HIGH` dentro do budget. Budgets padrÃ£o limitam tarefas `TRIVIAL`, `LOCALIZED`, `TRANSVERSAL` e `CRITICAL` a 1, 2, 4 e 6 agentes e a 1, 3, 5 e 6 chamadas de modelo. O contrato completo estÃ¡ em [contracts/protocol.md](contracts/protocol.md), a policy em [contracts/reasoning-policy.json](contracts/reasoning-policy.json) e o handoff em [contracts/handoff.schema.json](contracts/handoff.schema.json).

O runtime Ã© usado em todas as tarefas quando estiver disponÃ­vel; tarefas simples continuam sem subagentes e usam somente a classificaÃ§Ã£o e o registro mÃ­nimos:

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
  --to PLAN_APPROVED --reason "pedido direto e escopo inequÃ­voco"
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

O runtime calcula automaticamente horÃ¡rios e duraÃ§Ãµes. Tokens e crÃ©ditos sÃ£o valores observados fornecidos pelo executor; quando indisponÃ­veis, permanecem zero em vez de serem estimados. O banco histÃ³rico fica em `.jarvis/telemetry/jarvis.db`. Todo `.jarvis/` Ã© local e ignorado pelo Git; conteÃºdo clÃ­nico, faturamento real, credenciais e URLs privadas sÃ£o recusados.

O eval ao vivo Ã© opcional porque consome uma execuÃ§Ã£o do modelo:

~~~bash
python3 scripts/run_evals.py --live
python3 scripts/run_evals.py --live --case aghuse-new-rule --model gpt-5.6-luna
python3 scripts/run_evals.py --live --canary --save-results /tmp/jarvis-eval-v2
python3 scripts/run_evals.py --result-dir /tmp/jarvis-eval-v2 --compare-baseline
~~~

O modo ao vivo pede somente uma decisÃ£o estruturada de roteamento, usa sandbox somente leitura e proÃ­be chamadas externas e alteraÃ§Ãµes.

## Formato de handoff

Coordenadores e especialistas preservam o handoff schema 2.0 dentro do runtime V3: run/version, estÃ¡gio, classificaÃ§Ãµes, requisitos, arquivos com owner/finalidade, contratos, decisÃµes com provenance, validaÃ§Ãµes executadas e nÃ£o executadas, riscos, limitaÃ§Ãµes, blockers, stop reason e prÃ³ximo responsÃ¡vel.

