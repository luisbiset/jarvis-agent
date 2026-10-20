# Dashboard e API HTTP: fora do escopo do runtime atual

Data: 2026-10-05

## Objetivo

Registrar o limite explícito do produto atual: o repositório não contém dashboard nem API HTTP executável.

## Resumo executivo

O runtime canônico é uma CLI local. Ele produz envelopes JSON em stdout e não persiste sessões, eventos, telemetria ou artefatos de análise. Não existem rotas `/api`, telas, SSE, banco SQLite ou ações remotas implementadas neste pacote.

## Itens pendentes

| Prioridade | Item | Situação atual | O que falta |
|---|---|---|---|
| Prioridade | Item | Situação atual | Condição para iniciar |
|---|---|---|---|
| Alta | Dashboard web | Não implementada | Definir produto, autenticação, persistência e modelo de autorização. |
| Alta | API HTTP | Não implementada | Definir contrato versionado, autenticação, limites e observabilidade. |
| Alta | Persistência operacional | Não implementada | Definir dados permitidos por `SEC-001`, retenção e migração. |
| Média | Integração Redmine no runtime local | Não registrada | Criar adaptador explícito somente leitura e testes de contrato. |

## Dependências e ordem recomendada

1. Definir se dashboard/API fazem parte do produto.
2. Projetar autenticação, autorização, persistência segura e auditoria.
3. Implementar contratos e testes de integração antes da interface.

## Riscos

- Ações operacionais sem autorização podem causar execução indevida.
- Configurações editáveis podem alterar budget, policy ou segurança sem rastreabilidade.
- Integrações reais exigem credenciais, escopos mínimos e tratamento de falhas.
- Logs, prompts e resultados completos não devem ser persistidos sem sanitização.

## Critério de conclusão

Não tratar esta documentação como uma lista de capacidades entregues; ela registra itens ainda não iniciados.
