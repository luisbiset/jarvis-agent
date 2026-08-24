# Jarvis Agent

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
- `scripts/jarvis_runtime.py`: persiste estado, eventos, handoffs, context packs, cache de descoberta e métricas locais da V2.
- `contracts/`: schemas, políticas, fronteiras de papéis, padrões de tarefa e versão comportamental.
- `docs/TOPOLOGY.md`: topologia gerada automaticamente a partir dos manifests, agents e skills.
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

## Protocolo Jarvis V2

A V2 classifica cada execução por complexidade, risco, modo operacional e reasoning antes do roteamento. Budgets padrão limitam tarefas `TRIVIAL`, `LOCALIZED`, `TRANSVERSAL` e `CRITICAL` a 2 (um especialista e Auditor opcional), 3, 6 e 8 agentes, respectivamente. O contrato completo está em [contracts/protocol.md](contracts/protocol.md), e o handoff fechado em [contracts/handoff.schema.json](contracts/handoff.schema.json).

O runtime é opcional para tarefas simples e recomendado para fluxos multiagente:

```bash
python3 scripts/jarvis_runtime.py init \
  --task-id TASK-FICTICIA \
  --complexity LOCALIZED \
  --risk-class MEDIUM \
  --operational-mode ASSISTED_AUTOPILOT \
  --reasoning-class NORMAL

python3 scripts/jarvis_runtime.py transition --run-dir .jarvis/runs/<run_id> \
  --to PLAN_APPROVED --reason "pedido direto e escopo inequívoco"
python3 scripts/jarvis_runtime.py handoff --run-dir .jarvis/runs/<run_id>
python3 scripts/jarvis_runtime.py summary --run-dir .jarvis/runs/<run_id>
python3 scripts/jarvis_runtime.py dashboard
```

`.jarvis/` é local e ignorado pelo Git. Os eventos guardam metadados, caminhos, hashes e referências; conteúdo clínico, faturamento real, credenciais e URLs privadas são recusados.

O eval ao vivo é opcional porque consome uma execução do modelo:

~~~bash
python3 scripts/run_evals.py --live
python3 scripts/run_evals.py --live --case aghuse-new-rule --model gpt-5.6-luna
python3 scripts/run_evals.py --live --canary --save-results /tmp/jarvis-eval-v2
python3 scripts/run_evals.py --result-dir /tmp/jarvis-eval-v2 --compare-baseline
~~~

O modo ao vivo pede somente uma decisão estruturada de roteamento, usa sandbox somente leitura e proíbe chamadas externas e alterações.

## Formato de handoff

Coordenadores e especialistas usam o schema V2: run/version, estágio, classificações, requisitos, arquivos com owner/finalidade, contratos, decisões com provenance, validações executadas e não executadas, riscos, limitações, blockers, stop reason e próximo responsável.
