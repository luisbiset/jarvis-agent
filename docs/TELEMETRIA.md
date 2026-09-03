# Telemetria local do Jarvis V3.1

O runtime mantém três representações complementares sob `.jarvis/`:

- `runs/<run_id>/state.json`: snapshot atual da execução;
- `runs/<run_id>/events.jsonl`: trilha append-only de eventos;
- `telemetry/jarvis.db`: histórico SQLite para dashboard e exportação.

Esses arquivos são locais e ignorados pelo Git. Registre somente metadados; `SEC-001` proíbe credenciais, URLs privadas e conteúdo clínico ou de faturamento real.

`FLOW-003` torna a classificação obrigatória em toda tarefa, inclusive respostas simples e atividades somente leitura. O policy engine V3 decide conjuntamente modelo, reasoning e contexto a partir de sinais objetivos: `gpt-5.6-luna/low/SMALL`, `gpt-5.6-terra/medium/MEDIUM` ou `gpt-5.6-sol/high/LARGE`. Isso não torna subagentes obrigatórios: o objetivo é maximizar sucesso por unidade de custo. Quando o executor não expuser tokens ou créditos, informe `não informados` no fechamento em vez de tratá-los como consumo real zero.

## Decisão adaptativa

```bash
python3 scripts/jarvis_runtime.py reasoning-decide \
  --task-type DATABASE \
  --estimated-files 8 \
  --estimated-modules 2 \
  --database-migration \
  --production-critical \
  --tests-required \
  --ambiguity-score 2 \
  --complexity-score 4
```

No `init`, omita `--reasoning-class` e informe os mesmos sinais para deixar a decisão com a policy. O argumento antigo continua aceito apenas por compatibilidade.

## Fluxo mínimo

Inicialize a execução informando também o roteamento planejado:

```bash
python3 scripts/jarvis_runtime.py init \
  --task-id TASK-FICTICIA \
  --complexity LOCALIZED \
  --risk-class MEDIUM \
  --operational-mode ASSISTED_AUTOPILOT \
  --task-type BACKEND \
  --estimated-files 3 \
  --estimated-modules 1 \
  --tests-required \
  --complexity-score 3 \
  --agent-planned aghuse_backend \
  --agent-planned aghuse_qa
```

Para cada chamada de agente, inicie e finalize uma invocação própria:

```bash
python3 scripts/jarvis_runtime.py invocation-start \
  --run-dir .jarvis/runs/<run_id> \
  --agent aghuse_qa \
  --stage VALIDATING \
  --reasoning-effort medium \
  --parallel-batch validation-1

python3 scripts/jarvis_runtime.py invocation-finish \
  --run-dir .jarvis/runs/<run_id> \
  --invocation-id <invocation_id> \
  --status OK \
  --agent-result FOUND_ISSUE \
  --model-effective gpt-5.6-terra \
  --reasoning-effort-effective medium \
  --input-tokens 1200 \
  --cached-input-tokens 450 \
  --output-tokens 300 \
  --credits 1.4
```

Horários e duração são calculados pelo runtime. Cada `invocation-start` cria uma tentativa em `execution_attempts`; o fechamento acrescenta tokens, tools, arquivos, testes, sucesso e termination reason. Tokens e créditos não são estimados: informe apenas valores observados fornecidos pelo executor.

Após uma falha elegível de uma tentativa `MEDIUM`, consulte o evaluator antes do retry:

```bash
python3 scripts/jarvis_runtime.py evaluate \
  --run-dir .jarvis/runs/<run_id> \
  --no-success \
  --escalation-reason TEST_FAILURE \
  --previous-execution-id <invocation_id> \
  --tests-failed 1 \
  --changed-file src/Foo.java
```

Quando autorizado, o retorno será `HIGH`/`high` e incluirá o caminho do contexto compacto. Uma segunda escalada é recusada pelo budget.

## Findings, retrabalho e gate

```bash
python3 scripts/jarvis_runtime.py finding \
  --run-dir .jarvis/runs/<run_id> \
  --invocation-id <invocation_id> \
  --category REGRESSION \
  --severity HIGH \
  --actioned \
  --evidence-ref tests/FakeTest.java#failure

python3 scripts/jarvis_runtime.py transition \
  --run-dir .jarvis/runs/<run_id> \
  --to IMPLEMENTING \
  --reason "regressão encontrada pela validação" \
  --rework-origin QA \
  --rework-reason REGRESSION

python3 scripts/jarvis_runtime.py transition \
  --run-dir .jarvis/runs/<run_id> \
  --to IMPLEMENTING \
  --reason "mudanças solicitadas no gate" \
  --gate-decision CHANGES_REQUESTED \
  --gate-reason-code INSUFFICIENT_TEST \
  --rework-origin HUMAN \
  --rework-reason TEST
```

`APPROVED` recebe automaticamente o reason code `APPROVED_AS_PLANNED`. `CHANGES_REQUESTED` e `REJECTED` exigem um código da lista do contrato.

## Roteamento, dashboard e exportação

```bash
python3 scripts/jarvis_runtime.py route \
  --run-dir .jarvis/runs/<run_id> \
  --routing-outcome CORRECT \
  --agent-planned aghuse_backend \
  --agent-planned aghuse_qa

python3 scripts/jarvis_runtime.py dashboard
python3 scripts/jarvis_runtime.py export \
  --format json \
  --output /tmp/jarvis-telemetry.json
python3 scripts/jarvis_runtime.py export \
  --format csv \
  --output /tmp/jarvis-telemetry-csv
```

O dashboard agrega duração média/p50/p95, aprovação, sucesso na primeira tentativa, retrabalho, custo, budgets, roteamento, findings acionáveis e distribuições de bloqueios e rejeições humanas.

## Relatório de custo por execução

```bash
python3 scripts/jarvis_runtime.py report-cost --run-id <RUN_ID>
python3 scripts/jarvis_runtime.py report-cost --last 20 --group-by agent
python3 scripts/jarvis_runtime.py report-cost --last 20 --group-by stage
```

A saída contém chamadas, agentes únicos, tokens de entrada cached/uncached, tokens de saída, créditos observados, custo por arquivo alterado, participação de retries e as três etapas mais caras. Valores ausentes do executor permanecem neutros e não são estimados.

## Budgets proporcionais e fast path

Os limites padrão são 1/2/4/6 agentes para `TRIVIAL`/`LOCALIZED`/`TRANSVERSAL`/`CRITICAL` e 1/3/5/6 chamadas de modelo, sempre sob hard ceiling global. Uma tarefa `TRIVIAL`, `LOW` e `INSTANT`, limitada a um arquivo e um módulo e sem banco, segurança, arquitetura ou criticidade produtiva, recebe `execution_path=FAST_PATH`; as demais usam `STANDARD`.

`context_usage` e `cost_budget` começam obrigatoriamente em `OBSERVE_ONLY`. O runtime registra `CONTEXT_LIMIT_OBSERVED`, `COST_SOFT_LIMIT_OBSERVED` e `COST_HARD_LIMIT_OBSERVED`, mas não afirma interromper ferramentas ou uma inferência já iniciada. A ativação de bloqueios exige medições representativas e integração preventiva com o executor.

Associe uma execução dos evals à release e compare versões/configurações:

```bash
python3 scripts/jarvis_runtime.py eval-result \
  --routing-score 0.92 \
  --over-routing-score 0.95 \
  --under-routing-score 0.88 \
  --sequence-score 1.0 \
  --source-ref /tmp/jarvis-eval-v2/summary.json

python3 scripts/jarvis_runtime.py compare-releases
```

O runtime usa `jarvis_version` e `config_hash` atuais quando esses valores não são informados explicitamente.

## Technical Handoff e Teach-Back

`FLOW-004` reutiliza `complexity`, `risk_class` e `task_type` da execução. `TRIVIAL` não gera artefato; `LOCALIZED` gera resumo curto; regras de negócio, mudanças transversais e críticas geram handoff completo. Teach-Back é obrigatório somente para `CRITICAL` e fica limitado a seis turnos.

O input é um JSON com `summary`, `previous_behavior`, `new_behavior` e as listas `changed_components`, `execution_flow`, `decisions`, `risks`, `test_evidence` e `reading_order`. Cada evidência informa `description`, `path`, `symbol` e `reason`. O runtime confirma o símbolo no arquivo ou grava `UNKNOWN` sem inventar uma conclusão.

```bash
python3 scripts/jarvis_runtime.py technical-handoff \
  --run-dir .jarvis/runs/<run_id> \
  --input /tmp/technical-handoff-input.json \
  --workspace-root /caminho/do/projeto \
  --handoff-tokens 0 \
  --duration-ms 25

python3 scripts/jarvis_runtime.py technical-handoff-get \
  --task-id TASK-FICTICIA

python3 scripts/jarvis_runtime.py teachback-evaluate \
  --handoff-id <handoff_id> \
  --question-id Q1 \
  --answer "resposta do desenvolvedor" \
  --duration-ms 1200
```

A resposta livre é avaliada em memória e não é persistida. A tabela `teachback_evaluations` guarda somente `CORRECT`, `PARTIAL` ou `INCORRECT`, quantidade de conceitos identificados, duração e pedido de explicação adicional. O dashboard e os exports incluem custos e métricas da transferência de conhecimento separadamente.
