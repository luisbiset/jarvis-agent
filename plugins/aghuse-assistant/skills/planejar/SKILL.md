---
name: planejar
description: Cria um plano técnico independente pelo AGHUse Assistant, sem alterar arquivos.
---

Use para escopo, riscos, critérios de aceite e testes. A policy escolhe agents, modelo, reasoning e budget. Não inicie implementação automaticamente.

## Contrato de resposta

Gere internamente um objeto JSON válido no envelope PLAN definido em config/contracts/responses/envelope.schema.json e no schema específico da operação. Valide objective, assumptions, steps, dependencies, acceptance_criteria, validation_plan e risks dentro de data antes de apresentar o resultado pelo renderer Markdown. Não exponha o JSON técnico, prompts ou campos de política ao usuário.

## Execução no chat

Quando esta skill for usada dentro do ChatGPT/Codex, não solicite OPENAI_API_KEY, não use o provider HTTP local e não marque a operação como API_KEY_MISSING. Use o modelo da conversa e as ferramentas MCP disponíveis, especialmente o servidor Redmine para chamados. O contrato JSON PLAN deve ser aplicado à resposta final depois da análise.
