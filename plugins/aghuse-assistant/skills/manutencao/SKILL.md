---
name: manutencao
description: Mantém exclusivamente o AGHUse Assistant, seus plugins, skills, contratos, runtime, agentes, testes e documentação.
---

Use para analisar, planejar, implementar ou validar mudanças no próprio AGHUse Assistant. Não use para alterar o AGHUse clínico/faturamento.

O agente responsável é `aghuse_assistant`. Preserve alterações existentes, exija checkpoint antes de mudanças mutáveis, valide os contratos e execute testes proporcionais. Não persista credenciais, dados clínicos, URLs privadas ou prompts.

O resultado deve distinguir escopo assistant-only, arquivos alterados, testes executados, pendências, riscos e rollback. Mudanças externas ou operações compartilhadas permanecem fora do escopo.
