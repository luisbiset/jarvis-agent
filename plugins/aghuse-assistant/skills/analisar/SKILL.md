---
name: analisar
description: Executa uma analise tecnica independente, em modo somente leitura, sobre projeto, tarefa ou escopo, usando o Redmine apenas como fonte de contexto e requisitos.
---

Use para executar uma analise tecnica independente, em modo somente leitura, sobre um projeto, tarefa ou escopo. A policy escolhe agents, modelo, reasoning e budget. Nao inicie outra operacao.

O Redmine e apenas uma fonte de contexto e requisitos. A entrega e a analise tecnica realizada sobre o codigo, configuracao, banco e integracoes do projeto. Nunca encerre a operacao apenas com um resumo do chamado.

A resposta deve conter uma matriz de impacto por componente, com papel identificado, alteracao, classificacao, justificativa e evidencia. Nao apresente apenas uma lista de arquivos.

Antes das buscas, formule perguntas tecnicas verificaveis para cada requisito explicito. Uma referencia encontrada e apenas descoberta: siga chamadas, consultas, DTOs/VOs, validacoes, consumidores e saidas relevantes antes de concluir. Use os estados OPEN, DISCOVERED, VERIFIED, CONCLUDED e BLOCKED para hipoteses; evidencias placeholder nao confirmam requisitos.

O gate de suficiência deve separar o status da execucao do status tecnico da investigacao. Use COMPLETE somente quando todas as perguntas obrigatorias estiverem concluidas com fontes reais; caso contrario, use PARTIAL ou BLOCKED e preserve as perguntas pendentes e limitacoes. Nao force a secao "Causa provavel" quando a demanda for impacto, migracao ou nova funcionalidade.

## Contrato de resposta

Gere internamente um objeto JSON valido no envelope ANALYZE definido em `config/contracts/responses/envelope.schema.json` e no schema especifico da operacao. Valide `findings`, `impact`, `affected_files`, `risks`, `recommendations` e `evidence` dentro de `data` antes de apresentar o resultado pelo renderer Markdown. Nao exponha o JSON tecnico, prompts ou campos de politica ao usuario.

## Execucao no chat

Quando esta skill for usada dentro do ChatGPT/Codex, nao solicite `OPENAI_API_KEY`, nao use o provider HTTP local e nao marque a operacao como `API_KEY_MISSING`. Use o modelo da conversa e as ferramentas MCP disponiveis, especialmente o servidor Redmine para chamados. Apresente o resultado em secoes Markdown padronizadas: ANALISE CONCLUIDA, Resumo, Causa provavel, Arquivos envolvidos, Banco, Riscos e Recomendacao.

### Fluxo obrigatorio da analise

Quando o usuario informar um numero de tarefa, por exemplo `56213`, trate-o como `task_ref` e:

1. Consulte o chamado e, quando houver referencias, consulte tambem os chamados relacionados necessarios para descobrir o requisito completo, o comportamento esperado, limites, regras de aceite e evidencias.
2. Extraia do Redmine fatos e requisitos, separando-os de inferencias.
3. Localize no projeto os modulos, telas, entidades, tabelas, DAOs, servicos, validacoes, relatorios, integracoes, auditoria e testes relacionados ao requisito. Use busca textual e leitura dos fluxos relevantes; nao se limite ao nome ou a descricao do chamado.
4. Rastreie o dado ou comportamento ponta a ponta: entrada, transporte, regra, persistencia, leitura, saidas e historico. Para cada ponto encontrado, classifique se precisa ser alterado, apenas validado ou esta fora do escopo.
5. Confronte o requisito com a implementacao atual e produza conclusao tecnica: causa/estado atual, impacto, arquivos e banco afetados, riscos, lacunas de evidencia, recomendacao e testes necessarios.

Se o requisito ou o novo comportamento esperado nao estiver definido, registre a lacuna explicitamente e nao invente valores. Continue a analise com o que for verificavel. O objeto final da operacao e a analise tecnica do projeto, nunca o chamado Redmine.

Para uma analise de tarefa, a resposta deve distinguir claramente:

- **Fato do Redmine**: requisito, decisao, comentario ou chamado relacionado.
- **Evidencia do codigo**: arquivo, simbolo, linha ou mapeamento observado.
- **Conclusao tecnica**: impacto ou alteracao deduzida das evidencias.
- **Nao confirmado**: ponto que depende de banco, ambiente, requisito ou integracao nao disponivel.

Produza o contrato ANALYZE completo com base nessa investigacao.

Nao responda somente com os dados do chamado, nao use `list_issues` ou `get_issue` como operacao final e nao roteie esse caso para `redmine-workflows`. A resposta final deve conter os achados tecnicos, impacto, arquivos afetados, banco, riscos, recomendacoes, testes e evidencias do projeto. Se o Redmine nao estiver acessivel, registre essa limitacao em `evidence`/`risks`; nao trate o resumo da tarefa como analise concluida.
