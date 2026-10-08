---
name: validar
description: Executa uma validação independente pelo AGHUse Assistant, sem corrigir automaticamente.
---

Use para testes, diagnóstico de regressões e revisão de resultados. A policy escolhe agents, modelo, reasoning e budget. Não inicie outra operação.

## Contrato de resposta

Gere internamente um objeto JSON válido no envelope VALIDATE definido em config/contracts/responses/envelope.schema.json e no schema específico da operação. Valide checks, passed, failed, warnings, regressions, evidence e recommendation dentro de data antes de apresentar o resultado pelo renderer Markdown. Não exponha o JSON técnico, prompts ou campos de política ao usuário.

## Execução no chat

Quando esta skill for usada dentro do ChatGPT/Codex, não solicite OPENAI_API_KEY, não use o provider HTTP local e não marque a operação como API_KEY_MISSING. Use o modelo da conversa e as ferramentas MCP disponíveis, especialmente o servidor Redmine para chamados. O contrato JSON VALIDATE deve ser aplicado à resposta final depois da análise.
