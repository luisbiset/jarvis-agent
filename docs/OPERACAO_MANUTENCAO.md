# Operação MANUTENCAO

`MANUTENCAO` (`/manutencao`) é a operação exclusiva para o próprio AGHUse Assistant.

O agente `aghuse_assistant` pode analisar, planejar, implementar e validar mudanças em:

- código e runtime do assistant;
- skills, plugins e manifests;
- contratos, políticas e agentes;
- testes, fixtures e documentação.

A operação é mutável, exige confirmação humana e fica restrita ao projeto `aghuse-assistant`. Não deve alterar o AGHUse clínico/faturamento, banco, WildFly, Redmine compartilhado ou ambientes externos.

Exemplo:

```text
/manutencao revisar e corrigir o contrato da operação de análise
```
