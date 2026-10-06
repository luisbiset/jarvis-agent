# Dashboard — status de implementação

Documento de referência: `Jarvis_Dashboard_UI_UX.docx` (`JARVIS-DASHBOARD-UI-UX` v1.0).

## Implementado

| DASH-CHAT | Chat operacional | Implementado | Área de chat integrada ao `jarvis_chat`, consulta RAG antes do planejamento, sessões com hashes/resumos seguros e API `/api/chat/sessions` |
| DASH-CHECKPOINT | Checkpoint de execução | Implementado | Snapshots seguros em `.jarvis/runs/<run_id>/checkpoints` e exibição no detalhe da execução |
| DASH-ACTIONS | Ações Runtime | Parcial implementado | `PAUSE`, `RESUME`, `APPROVE` e `RETRY` delegados ao Runtime, com auditoria local em `/api/audit` |
| DASH-SEARCH | Busca global inicial | Implementado | `/api/search` para execuções e sessões de chat, sem persistir conteúdo sensível |
| DASH-COMMANDS | Registro de comandos | Implementado | `/api/commands` com indicação de comandos mutáveis e necessidade de confirmação |
| DASH-DIFF | Diff local | Implementado | `/api/runs/<run_id>/diff`, somente leitura, limitado ao diff da worktree |
| DASH-METRICS | Métricas filtráveis | Implementado | `/api/models/usage` aceita filtros de modelo, reasoning e período quando disponíveis no schema |
| DASH-SERIES | Séries de métricas | Implementado | `/api/metrics/series` agrupa chamadas, tokens e créditos por data/modelo/reasoning sem estimar timestamps ausentes |
| DASH-E2E | Contratos HTTP locais | Implementado | Teste de servidor local cobre comandos, settings, integrações, busca e criação segura de draft |
| DASH-AGENTS | Detalhe de agents | Implementado | `GET /api/agents/<agent>` retorna histórico, tarefas, findings e consumo observado |
| DASH-CONTRACTS | Estados operacionais | Implementado | Runtime, `execution-state.schema.json` e `handoff.schema.json` compartilham estados de pausa e espera |
| DASH-SETTINGS | Configuração revisionada | Implementado | `/api/settings`, drafts, aplicação confirmada e rollback auditado; grava apenas overlay local em `.jarvis/dashboard/active-settings.json` |
| DASH-INTEGRATIONS | Registro de integrações | Implementado para Redmine | `POST/GET /api/integrations`, adaptador MCP local via JSON-RPC, ping, capabilities `redmine.read.*`, auditoria e bloqueio de escrita |

| Requisito | Situação | Evidência |
|---|---|---|
| DASH-001 iniciar task | Implementado | `POST /api/tasks`, validação e delegação ao Runtime V3 |
| DASH-002 listar/filtrar tasks | Implementado | `GET /api/runs` com busca, status, complexidade e risco |
| DASH-003 detalhe de task | Implementado | `GET /api/runs/<run_id>` e `/run/<run_id>` |
| DASH-004 etapas/status | Implementado | timeline persistida em `transitions` |
| DASH-005 logs correlacionados | Implementado | eventos seguros de `events.jsonl` no detalhe |
| DASH-006 consumo de modelos/tokens | Implementado | `GET /api/models/usage` |
| DASH-007 agentes | Implementado | `GET /api/agents` e métricas do Runtime V3 |
| DASH-013 Evidence Explorer | Implementado | `GET /api/evidence` retorna findings e grafo seguro de agents produtores, referências e relações |
| Atualização automática | Implementado | polling de 15 segundos na interface atual |
| Estados desconhecidos seguros | Implementado | `UNKNOWN/NOT_OBSERVED` preservado |

## Parcialmente implementado

| Requisito | Limitação atual |
|---|---|
| Task Detail visual | A API entrega timeline e dados; a tela dedicada ainda é simples |
| Agents visual | Métricas disponíveis pela API, sem página dedicada |
| Logs | Eventos persistidos são exibidos sem streaming ou filtros avançados |
| Models/Metrics | Totais, filtros por modelo/reasoning/período e gráfico leve de séries disponíveis; drill-down avançado ainda pode evoluir |
| Evidence | Findings disponíveis; consumidores, arquivos e resumos ricos dependem de persistência adicional |
| Ações | Criação é executada; demais ações precisam de workflow supervisionado no Runtime |

## Não implementado por inviabilidade atual

| Requisito | Motivo |
|---|---|
| Integrações/MCP reais | Redmine integrado; outros MCPs externos ainda dependem de adaptadores específicos |
| Settings editáveis | Alterar policy/configuração exige contrato de autorização e auditoria próprio |
| Prompt/output completos | Não devem ser persistidos por segurança e privacidade |
| Busca global completa | Falta índice unificado de tasks, evidências, erros e integrações |
| Command Palette completa | Depende das ações e destinos finais da busca global |

## Garantias

- A dashboard permanece local por padrão (`127.0.0.1`).
- A criação de task não executa banco, deploy, Redmine ou infraestrutura externa.
- Endpoints não retornam prompts, credenciais, URLs privadas ou conteúdo clínico.
- Ações não suportadas não são simuladas como concluídas.
- O Runtime V3 continua sendo a fonte de verdade.
