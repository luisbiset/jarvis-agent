---
name: aghuse-preparacao-tarefa
description: Preparar uma tarefa do AGHUse antes da implementação, identificando número, branch, commits, módulos, alterações locais e dependências de banco ou segurança. Usar para iniciar chamados, conferir prontidão ou delimitar o escopo; não usar como substituto da implementação.
---

# Preparação de tarefa do AGHUse

Localize a raiz com `aghu/pom.xml` e `aghu-entidades/pom.xml` e trabalhe somente em leitura. Execute o subcomando `contexto` de `scripts/aghuse_automacao.py` no plugin para obter o baseline estruturado quando o repositório Git estiver disponível.

## Verificar

- Relacionar tarefa, branch e commits sem presumir que todo número encontrado representa o chamado atual.
- Registrar alterações rastreadas e não rastreadas como trabalho preexistente do usuário.
- Mapear arquivos e módulos possivelmente afetados.
- Procurar indícios de DDL, entidades, auditoria, mensagens, páginas protegidas, permissões e menus.
- Consultar Redmine apenas quando solicitado ou necessário e disponível, mantendo a etapa somente leitura.
- Separar pré-requisitos confirmados, indícios e perguntas realmente bloqueantes.

## Entregar

Informar contexto Git, escopo provável, dependências, riscos, validações recomendadas e pendências. Não editar, executar banco, atualizar segurança, fazer deploy, commit ou push nesta etapa.
