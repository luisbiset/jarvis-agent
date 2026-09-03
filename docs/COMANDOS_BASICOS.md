# Comandos básicos para economizar créditos

## Regra principal

Comece com **uma única skill**, informe o escopo exato e peça a menor validação suficiente.

O Jarvis aplica automaticamente `FLOW-003` em toda tarefa: classifica complexidade, risco, modo, reasoning e budget, usa o mínimo de agentes e apresenta uma linha curta de métricas no fechamento.

Modelo para copiar:

> `$skill` Faça **[objetivo]** em **[arquivo/módulo]**. Considere **[erro ou requisito]**. Termine quando **[critério verificável]**. Não use subagentes. Valide apenas o escopo alterado. Não faça commit, push, deploy nem alterações externas.

## Comandos mais usados

### Trabalhar no AGHUse

> `$aghuse-development` Corrija **[problema]** no módulo **[módulo]**. Não use subagentes. Execute somente os testes diretamente afetados. Não faça commit.

### Trabalhar no SFA

> `$sfa-development` Corrija **[problema]** em **[sfa ou sfa-client]**. Não use subagentes. Valide somente o componente alterado. Não faça commit.

### Consultar um chamado

> `$redmine-workflows` Resuma o chamado **[número]**, destacando objetivo, critérios e pendências. Somente leitura.

### Diagnosticar antes de corrigir

> `$aghuse-diagnostico-logs` Analise este erro e informe causa raiz, arquivo provável e correção recomendada. Não implemente.

### Preparar uma tarefa AGHUse

> `$aghuse-preparacao-tarefa` Verifique a tarefa **[número]**, branch, módulos e dependências. Somente leitura e sem subagentes.

### Executar a validação mínima

> `$aghuse-validacao-direcionada` Valide somente os arquivos alterados. Não execute build completo se um teste ou módulo direcionado for suficiente.

### Conferir antes de entregar

> `$aghuse-verificacao-entrega` Revise o diff e as validações desta tarefa. Somente leitura. Não faça commit, push ou atualização no Redmine.

### Criar roteiro de homologação

> `$aghuse-roteiro-homologacao` Crie um roteiro curto com pré-condições, passos e resultados esperados. Use dados fictícios e não execute a interface.

## Quando usar mais raciocínio

- **Low:** explicação, busca localizada, ajuste de texto ou tarefa mecânica.
- **Medium:** correção localizada e implementação comum.
- **High:** regra ambígua, investigação difícil ou mudança de risco alto.
- Use `/plan` somente quando o escopo estiver incerto ou envolver várias etapas.

## Regras para gastar menos

1. Use uma conversa nova para cada tarefa ou sistema.
2. Informe arquivo, módulo, erro e critério de conclusão logo no primeiro pedido.
3. Para tarefa simples, escreva: **“Não use subagentes.”** Cada subagente realiza trabalho próprio e aumenta o consumo.
4. Não combine várias skills de coordenação. Escolha `$aghuse-development`, `$sfa-development` ou `$redmine-workflows`.
5. Use uma skill AGHUse especializada somente quando quiser aquela etapa isolada.
6. Peça **“somente leitura”** quando não quiser implementação.
7. Peça testes e builds direcionados; deixe a suíte completa para mudanças transversais ou para o gate final.
8. Na mesma tarefa, continue na conversa atual. Ao mudar de assunto, abra outra para evitar contexto acumulado.
9. Não cole logs inteiros quando algumas linhas do erro e o stack trace relevante forem suficientes.
10. Não peça revisão, homologação e documentação se esses resultados não forem necessários para a entrega.

## Escolha rápida

| Necessidade | Use |
|---|---|
| Mudança no AGHUse | `$aghuse-development` |
| Mudança no SFA | `$sfa-development` |
| Consulta ou ação no Redmine | `$redmine-workflows` |
| Log do AGHUse | `$aghuse-diagnostico-logs` |
| Teste mínimo do AGHUse | `$aghuse-validacao-direcionada` |
| Conferência final do AGHUse | `$aghuse-verificacao-entrega` |

## Referências oficiais

- [Boas práticas do Codex](https://learn.chatgpt.com/guides/best-practices)
- [Como escrever prompts](https://learn.chatgpt.com/docs/prompting)
- [Subagentes e consumo adicional](https://learn.chatgpt.com/docs/agent-configuration/subagents)
- [Como as skills são ativadas](https://developers.openai.com/plugins/concepts/skills)
