# Dashboard — status de implementação

Documento de referência: `Jarvis_Dashboard_UI_UX.docx` (`JARVIS-DASHBOARD-UI-UX` v1.0).

## Implementado

| Requisito | Situação | Evidência |
|---|---|---|
| DASH-001 iniciar task | Implementado | `POST /api/tasks`, validação e delegação ao Runtime V3 |
| DASH-002 listar/filtrar tasks | Implementado | `GET /api/runs` com busca, status, complexidade e risco |
| DASH-003 detalhe de task | Implementado | `GET /api/runs/<run_id>` e `/run/<run_id>` |
| DASH-004 etapas/status | Implementado | timeline persistida em `transitions` |
| DASH-005 logs correlacionados | Implementado | eventos seguros de `events.jsonl` no detalhe |
| DASH-006 consumo de modelos/tokens | Implementado | `GET /api/models/usage` |
| DASH-007 agentes | Implementado | `GET /api/agents` e métricas do Runtime V3 |
| DASH-013 Evidence Explorer básico | Implementado | `GET /api/evidence` baseado em findings |
| Atualização automática | Implementado | polling de 15 segundos na interface atual |
| Estados desconhecidos seguros | Implementado | `UNKNOWN/NOT_OBSERVED` preservado |

## Parcialmente implementado

| Requisito | Limitação atual |
|---|---|
| Task Detail visual | A API entrega timeline e dados; a tela dedicada ainda é simples |
| Agents visual | Métricas disponíveis pela API, sem página dedicada |
| Logs | Eventos persistidos são exibidos sem streaming ou filtros avançados |
| Models/Metrics | Totais e agrupamentos disponíveis; gráficos e filtros temporais ainda não |
| Evidence | Findings disponíveis; consumidores, arquivos e resumos ricos dependem de persistência adicional |
| Ações | Criação é executada; demais ações precisam de workflow supervisionado no Runtime |

## Não implementado por inviabilidade atual

| Requisito | Motivo |
|---|---|
| Integrações/MCP reais | Não há contrato seguro de capabilities/health/calls persistido |
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
