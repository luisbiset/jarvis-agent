---
name: implementar
description: Executa uma implementação controlada pelo AGHUse Assistant, com aprovação e checkpoint.
---

Use para alterações aprovadas. A policy e o Runtime controlam agents, modelo, reasoning e budget. Não contorne gates ou isolamento.

## Contrato de resposta

Gere internamente um objeto JSON válido no envelope IMPLEMENT definido em config/contracts/responses/envelope.schema.json e no schema específico da operação. Valide changes, files_changed, tests_executed, tests_passed, pending_items, rollback_notes e approval_required dentro de data antes de apresentar o resultado pelo renderer Markdown. Não exponha o JSON técnico, prompts ou campos de política ao usuário.

## Execução no chat

Quando esta skill for usada dentro do ChatGPT/Codex, não solicite OPENAI_API_KEY, não use o provider HTTP local e não marque a operação como API_KEY_MISSING. Use o modelo da conversa e as ferramentas MCP disponíveis, especialmente o servidor Redmine para chamados. O contrato JSON IMPLEMENT deve ser aplicado à resposta final depois da análise.
