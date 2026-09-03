# Changelog comportamental

## 3.1.0 - 2026-08-27

- `FLOW-004` adiciona Technical Handoff baseado em evidências, mapa de leitura, Teach-Back proporcional e recuperação por task.
- Respostas livres do Teach-Back não são persistidas; somente resultado, conceitos cobertos e duração entram na telemetria.
- Fan-out padrão reduzido para 1/2/4/6 agentes e chamadas de modelo limitadas por complexidade sob hard ceiling global.
- `FAST_PATH` formalizado para tarefas triviais de baixo risco.
- Limites de contexto e custo adicionados em `OBSERVE_ONLY`, sem alegar bloqueio preventivo do executor.
- Relatório de custo por run, agente e estágio adicionado com métricas de cache, retries e arquivos alterados.

## 3.0.0 - 2026-08-26

- Reasoning passou a ser decidido por policy central e versionada a partir de sinais objetivos.
- Perfis deixaram de fixar `model_reasoning_effort`; novas chamadas recebem o effort decidido pelo runtime.
- Tentativas são persistidas individualmente com reasoning inicial/efetivo, tokens, custo, arquivos, tools, testes, sucesso e termination reason.
- Uma tentativa `MEDIUM` pode escalar uma única vez para `HIGH` por sinais verificáveis, reutilizando contexto compacto.
- Budgets limitam tentativas, escaladas e profundidade de child agents; `HIGH` nunca escala novamente.
- Dashboard e exportação agregam sucesso, custo e escaladas por reasoning.

## 2.1.0 - 2026-08-24

- Removidos o plugin, a skill e o agente `sesab-orchestrator`; o usuário seleciona diretamente SFA ou AGHUse.
- Guias movidos para `docs/` e exemplos transversais retirados dos contratos e evals.
- Telemetria passou a medir automaticamente duração de runs e invocações, uso separado de tokens/créditos, modelo e reasoning.
- Invocações, findings, transições, handoffs, gates humanos e decisões agora possuem histórico local em SQLite e JSONL.
- O runtime passou a medir retrabalho, efetividade dos agentes, orçamento, roteamento, stop reasons e sucesso na primeira tentativa.
- Dashboard local e exportações JSON/CSV permitem comparar custo, qualidade, latência e roteamento sem serviço externo.
- Snapshots de roteamento e scores de eval podem ser comparados por release e `config_hash`.
- `FLOW-003` tornou obrigatórias em toda tarefa a classificação de complexidade, risco, modo, reasoning e budget, a telemetria quando disponível e a linha resumida de métricas no fechamento.

## 2.0.0 - 2026-08-24

- Handoffs passaram a ter schema fechado, provenance, ownership, validações ausentes e stop reasons.
- Roteamento passou a declarar complexidade, risco, modo, reasoning e budgets.
- O fluxo ganhou estados persistidos, eventos append-only e gate de explicabilidade.
- QA, Auditor do diff, Reviewer e QA de homologação passaram a responder perguntas distintas.
- Evals passaram a medir sequência, over-routing, under-routing e segurança de confirmação.
