# Changelog comportamental

## 2.1.0 - 2026-08-24

- Removidos o plugin, a skill e o agente `sesab-orchestrator`; o usuário seleciona diretamente SFA ou AGHUse.
- Guias movidos para `docs/` e exemplos transversais retirados dos contratos e evals.

## 2.0.0 - 2026-08-24

- Handoffs passaram a ter schema fechado, provenance, ownership, validações ausentes e stop reasons.
- Roteamento passou a declarar complexidade, risco, modo, reasoning e budgets.
- O fluxo ganhou estados persistidos, eventos append-only e gate de explicabilidade.
- QA, Auditor do diff, Reviewer e QA de homologação passaram a responder perguntas distintas.
- Evals passaram a medir sequência, over-routing, under-routing e segurança de confirmação.
